# Databricks notebook source
# MAGIC %md
# MAGIC # 03 集計：顧客 360（関心スコア・セグメント）とアンケート集計を作る
# MAGIC - 名寄せ：CustomerLake Profile Agents の出力 `identity_xref` で、Qualtrics 回答者・CASIO ID 会員・オンラインストア顧客を1人の顧客（profile_id）にまとめる
# MAGIC - 関心スコア：アンケートの回答（関心・利用シーン）＋AI 分類の関心タグ＋保有製品＋購入履歴を、新しい回答ほど重く足し合わせる



# COMMAND ----------
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "casio_cx")
dbutils.widgets.text("idr_schema", "casio_cx_idr")
C = dbutils.widgets.get("catalog"); S = dbutils.widgets.get("schema"); IDR = dbutils.widgets.get("idr_schema")
spark.sql(f"USE CATALOG {C}")
DIMS = ["outdoor", "sports", "business", "luxury", "fashion", "music", "study", "office", "tech", "wellness", "family"]
SEG = {"outdoor": "アウトドア・アクティブ派", "sports": "アウトドア・アクティブ派", "business": "ビジネス・上質派", "luxury": "ビジネス・上質派",
       "fashion": "ファッション派", "music": "音楽・ホビー派", "study": "学び・実務派", "office": "学び・実務派",
       "wellness": "癒やし・ギフト派", "family": "癒やし・ギフト派"}

# COMMAND ----------
# MAGIC %md ## 1. 名寄せ結果（CustomerLake Profile Agents）を取り込む

# COMMAND ----------
has_idr = spark.catalog.tableExists(f"{C}.{IDR}.identity_xref")
print("CustomerLake identity_xref:", has_idr)
if has_idr:
    spark.sql(f"""CREATE OR REPLACE TEMP VIEW xref AS
      SELECT CASE WHEN lower(id.source) LIKE '%survey%' THEN 'survey'
                  WHEN lower(id.source) LIKE '%member%' OR lower(id.source) LIKE '%casio_id%' THEN 'member'
                  WHEN lower(id.source) LIKE '%store%' THEN 'store' END AS src,
             id.record_id AS record_id, profile_id
      FROM {C}.{IDR}.identity_xref""")
else:
    spark.sql("CREATE OR REPLACE TEMP VIEW xref AS SELECT CAST(NULL AS STRING) src, CAST(NULL AS STRING) record_id, CAST(NULL AS STRING) profile_id WHERE 1=0")

# 名寄せ前の新しい回答者は「Q-<contact_id>」として仮の顧客にする（次の名寄せで統合される）
spark.sql(f"""CREATE OR REPLACE TABLE {S}.gold_contact_profile COMMENT 'Qualtrics 連絡先 → 名寄せ後の顧客 ID' AS
SELECT r.contact_id, coalesce(x.profile_id, concat('Q-', r.contact_id)) AS profile_id, x.profile_id IS NOT NULL AS resolved
FROM {S}.src_survey_respondents r LEFT JOIN xref x ON x.src = 'survey' AND x.record_id = r.contact_id""")
spark.sql(f"""CREATE OR REPLACE TEMP VIEW member_p AS
SELECT m.*, coalesce(x.profile_id, concat('M-', m.member_id)) AS profile_id
FROM {S}.src_casio_id_members m LEFT JOIN xref x ON x.src = 'member' AND x.record_id = m.member_id""")
spark.sql(f"""CREATE OR REPLACE TEMP VIEW store_p AS
SELECT s.*, coalesce(x.profile_id, concat('S-', s.customer_no)) AS profile_id
FROM {S}.src_online_store_customers s LEFT JOIN xref x ON x.src = 'store' AND x.record_id = s.customer_no""")
spark.sql(f"""CREATE OR REPLACE TEMP VIEW resp_p AS
SELECT r.*, cp.profile_id, l.sentiment, l.topics, l.interest_tags, l.purchase_intent, l.summary,
       row_number() OVER (PARTITION BY cp.profile_id ORDER BY r.submitted_at DESC) AS recency_rank
FROM {S}.silver_responses r JOIN {S}.gold_contact_profile cp USING (contact_id)
LEFT JOIN {S}.response_labels l USING (response_id)""")

# COMMAND ----------
# MAGIC %md ## 2. 関心スコア（新しい回答ほど重く。最新の回答は 3 倍）

# COMMAND ----------
spark.sql(f"""CREATE OR REPLACE TEMP VIEW signals AS
WITH r AS (SELECT *, pow(0.5, datediff(current_date(), to_date(submitted_at)) / 120.0) * IF(recency_rank = 1, 3.0, 1.0) AS w FROM resp_p)
SELECT profile_id, dim, w * 1.0 AS v FROM r LATERAL VIEW explode(interests) e AS dim
UNION ALL SELECT profile_id, dim, w * 0.7 FROM r LATERAL VIEW explode(coalesce(interest_tags, array())) e AS dim
UNION ALL SELECT o.profile_id, t.dim, 0.3 * o.w FROM (SELECT profile_id, w, explode(owned_products) AS pid FROM r) o
          JOIN (SELECT product_id, explode(tags) AS dim FROM {S}.products) t ON t.product_id = o.pid
UNION ALL SELECT s.profile_id, t.dim, 0.5 * pow(0.5, datediff(current_date(), to_date(o.order_date)) / 365.0)
          FROM {S}.online_store_orders o JOIN store_p s USING (customer_no)
          JOIN (SELECT product_id, explode(tags) AS dim FROM {S}.products) t USING (product_id)""")
score_cols = ", ".join(f"round(coalesce(max(IF(dim = '{d}', v, NULL)) / greatest(max(v), 1e-9), 0), 3) AS score_{d}" for d in DIMS)
spark.sql(f"""CREATE OR REPLACE TEMP VIEW scores AS
SELECT profile_id, {score_cols} FROM (SELECT profile_id, dim, sum(v) v FROM signals WHERE dim IS NOT NULL GROUP BY 1, 2) GROUP BY profile_id""")
seg_case = "CASE " + " ".join(
    f"WHEN g_{k} = greatest({', '.join('g_' + x for x in ['act', 'biz', 'fas', 'mus', 'stu', 'wel'])}) THEN '{v}'"
    for k, v in [("act", "アウトドア・アクティブ派"), ("biz", "ビジネス・上質派"), ("fas", "ファッション派"), ("mus", "音楽・ホビー派"),
                 ("stu", "学び・実務派"), ("wel", "癒やし・ギフト派")]) + " END"
top_expr = "array_sort(array(" + ", ".join(f"named_struct('d', '{d}', 's', score_{d})" for d in DIMS) + "), (a, b) -> CASE WHEN a.s > b.s THEN -1 WHEN a.s < b.s THEN 1 ELSE 0 END)"

# COMMAND ----------
# MAGIC %md ## 3. 顧客 360（CustomerLake の Campaign Agents がエンティティとして使う）

# COMMAND ----------
spark.sql(f"""CREATE OR REPLACE TABLE {S}.gold_customer_360
COMMENT '顧客 360：名寄せ後の顧客ごとのプロフィール・関心スコア・アンケート集計・購入集計（CustomerLake エンティティのプロファイル表）' AS
WITH ids AS (SELECT profile_id FROM member_p UNION SELECT profile_id FROM store_p UNION SELECT profile_id FROM {S}.gold_contact_profile),
mem AS (SELECT profile_id, max_by(struct(concat(last_name, ' ', first_name) AS name, email, phone, prefecture, city, birth_date, gender, newsletter_optin, member_id), registered_at) m FROM member_p GROUP BY 1),
sto AS (SELECT profile_id, max_by(struct(full_name AS name, email, tel, customer_no), created_at) s FROM store_p GROUP BY 1),
res AS (SELECT cp.profile_id, max_by(struct(r.full_name AS name, r.email, r.prefecture, r.age_band, r.gender, r.contact_id), r.updated_at) q, bool_and(cp.resolved) resolved
        FROM {S}.src_survey_respondents r JOIN {S}.gold_contact_profile cp USING (contact_id) GROUP BY 1),
ans AS (SELECT profile_id, count(*) response_count, round(avg(nps), 1) avg_nps, max_by(nps, submitted_at) last_nps,
               max(submitted_at) last_response_at, round(avg(IF(sentiment = 'positive', 1, 0)), 2) positive_ratio,
               max_by(next_purchase_category, submitted_at) next_purchase_category, max_by(budget_band, submitted_at) budget_band,
               max_by(comment, submitted_at) latest_comment, max_by(summary, submitted_at) latest_summary,
               slice(array_distinct(flatten(collect_list(owned_products))), 1, 20) owned_from_survey,
               max_by(survey_name, submitted_at) latest_survey
        FROM resp_p GROUP BY 1),
tp AS (SELECT profile_id, slice(transform(array_sort(collect_list(struct(-n AS k, topic))), x -> x.topic), 1, 3) top_topics
       FROM (SELECT profile_id, topic, count(*) n FROM resp_p LATERAL VIEW explode(coalesce(topics, array())) e AS topic GROUP BY 1, 2) GROUP BY 1),
ord AS (SELECT s.profile_id, count(*) order_count, sum(amount) total_spend, max(order_date) last_order_at, collect_set(product_id) bought
        FROM {S}.online_store_orders o JOIN store_p s USING (customer_no) GROUP BY 1),
base AS (
SELECT i.profile_id,
       coalesce(m.m.name, s.s.name, q.q.name) AS display_name,
       coalesce(m.m.email, s.s.email, q.q.email) AS email,
       coalesce(m.m.prefecture, q.q.prefecture) AS prefecture,
       coalesce(q.q.age_band, CASE WHEN m.m.birth_date IS NOT NULL THEN concat(CAST(floor(datediff(current_date(), m.m.birth_date) / 3652.5) * 10 AS INT), '代') END) AS age_band,
       coalesce(m.m.gender, q.q.gender) AS gender,
       m.m.member_id, s.s.customer_no, q.q.contact_id,
       concat_ws('・', IF(m.m IS NOT NULL, 'CASIO ID', NULL), IF(s.s IS NOT NULL, 'オンラインストア', NULL), IF(q.q IS NOT NULL, 'Qualtrics', NULL)) AS sources,
       (CASE WHEN m.m IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN s.s IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN q.q IS NOT NULL THEN 1 ELSE 0 END) AS source_count,
       coalesce(m.m.newsletter_optin, false) AS newsletter_optin,
       sc.* EXCEPT (profile_id),
       coalesce(a.response_count, 0) AS response_count, a.avg_nps, a.last_nps,
       CASE WHEN a.last_nps >= 9 THEN '推奨者' WHEN a.last_nps >= 7 THEN '中立者' WHEN a.last_nps IS NOT NULL THEN '批判者' END AS nps_group,
       a.last_response_at, a.positive_ratio, a.next_purchase_category, a.budget_band, a.latest_comment, a.latest_summary, a.latest_survey,
       tp.top_topics,
       array_distinct(concat(coalesce(a.owned_from_survey, array()), coalesce(o.bought, array()))) AS owned_products,
       coalesce(o.order_count, 0) AS order_count, coalesce(o.total_spend, 0) AS total_spend, o.last_order_at
FROM ids i LEFT JOIN mem m USING (profile_id) LEFT JOIN sto s USING (profile_id) LEFT JOIN res q USING (profile_id)
LEFT JOIN scores sc USING (profile_id) LEFT JOIN ans a USING (profile_id) LEFT JOIN tp USING (profile_id) LEFT JOIN ord o USING (profile_id))
SELECT * EXCEPT (g_act, g_biz, g_fas, g_mus, g_stu, g_wel), CASE WHEN score_outdoor IS NULL THEN '未分類' ELSE {seg_case} END AS segment,
       transform(filter(slice({top_expr}, 1, 3), x -> x.s > 0), x -> x.d) AS top_interests,
       current_timestamp() AS updated_at
FROM (SELECT *, coalesce(greatest(score_outdoor, score_sports), 0) g_act, coalesce(greatest(score_business, score_luxury), 0) g_biz,
             coalesce(score_fashion, 0) g_fas, coalesce(score_music, 0) g_mus, coalesce(greatest(score_study, score_office), 0) g_stu,
             coalesce(greatest(score_wellness, score_family), 0) g_wel FROM base)
""")

# COMMAND ----------
# MAGIC %md ## 4. セグメント集計・話題集計・セグメント別の製品人気

# COMMAND ----------
spark.sql(f"""CREATE OR REPLACE TABLE {S}.gold_segment_summary COMMENT 'セグメント別のアンケート集計' AS
SELECT segment, count(*) customers, sum(response_count) responses, round(avg(avg_nps), 2) avg_nps,
       round(100 * (avg(IF(nps_group = '推奨者', 1, 0)) - avg(IF(nps_group = '批判者', 1, 0))), 1) nps_score,
       round(avg(positive_ratio), 2) positive_ratio, round(avg(total_spend)) avg_spend,
       sum(IF(newsletter_optin, 1, 0)) optin_customers, current_timestamp() updated_at
FROM {S}.gold_customer_360 WHERE response_count > 0 GROUP BY segment""")
spark.sql(f"""CREATE OR REPLACE TABLE {S}.gold_topic_summary COMMENT 'セグメント×話題×感情の件数（AI 分類の集計）' AS
SELECT c.segment, topic, sum(IF(r.sentiment = 'positive', 1, 0)) positive, sum(IF(r.sentiment = 'neutral', 1, 0)) neutral,
       sum(IF(r.sentiment = 'negative', 1, 0)) negative, count(*) total, current_timestamp() updated_at
FROM (SELECT profile_id, sentiment, explode(coalesce(topics, array())) AS topic FROM resp_p) r JOIN {S}.gold_customer_360 c USING (profile_id)
GROUP BY 1, 2""")
spark.sql(f"""CREATE OR REPLACE TABLE {S}.gold_segment_product_affinity COMMENT 'セグメント別の製品人気（保有・購入の割合を 0〜1 に正規化）' AS
WITH own AS (SELECT c.segment, pid AS product_id, count(DISTINCT c.profile_id) n FROM {S}.gold_customer_360 c LATERAL VIEW explode(owned_products) e AS pid GROUP BY 1, 2),
seg AS (SELECT segment, count(*) n FROM {S}.gold_customer_360 GROUP BY 1)
SELECT o.segment, o.product_id, o.n owners, round(o.n / s.n, 4) owner_ratio,
       round(o.n / max(o.n) OVER (PARTITION BY o.segment), 3) affinity
FROM own o JOIN seg s USING (segment)""")

for t in ["gold_customer_360", "gold_segment_summary", "gold_topic_summary", "gold_contact_profile"]:
    print(t, spark.table(f"{S}.{t}").count())
