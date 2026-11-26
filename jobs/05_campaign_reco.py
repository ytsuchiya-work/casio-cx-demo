# Databricks notebook source
# MAGIC %md
# MAGIC # 05 キャンペーン対象とレコメンド
# MAGIC - CustomerLake Campaign Agents で作ったオーディエンス（UC ビュー）から対象者を取り出す
# MAGIC - 関心スコア × セグメントの人気 × 予算 × 次に欲しいカテゴリ × キャンペーンで、顧客ごとに上位 5 製品を選ぶ

# COMMAND ----------
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "casio_cx")
C = dbutils.widgets.get("catalog"); S = dbutils.widgets.get("schema")
spark.sql(f"USE CATALOG {C}")
LABEL = {"outdoor": "アウトドア", "sports": "スポーツ", "business": "ビジネス", "luxury": "上質・高級", "fashion": "ファッション", "music": "音楽", "study": "学び", "office": "事務・実務", "tech": "スマート連携", "wellness": "癒やし", "family": "家族・ギフト"}
LABEL_CASE = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in LABEL.items())
DIMS = ["outdoor", "sports", "business", "luxury", "fashion", "music", "study", "office", "tech", "wellness", "family"]

# COMMAND ----------
# MAGIC %md ## 5. キャンペーン対象（CustomerLake Campaign Agents のオーディエンス）

# COMMAND ----------
spark.sql(f"""CREATE TABLE IF NOT EXISTS {S}.campaign_audiences (audience_id STRING, audience_name STRING, series STRING, offer STRING, active BOOLEAN)
COMMENT 'アプリで使うオーディエンス（CustomerLake で作成）の一覧'""")
auds = [r.asDict() for r in spark.table(f"{S}.campaign_audiences").where("active").collect()]
parts = []
for a in auds:
    if spark.catalog.tableExists(f"{C}.audiences.`{a['audience_id']}`"):
        parts.append(f"SELECT CAST(CDP_PROFILE_ID AS STRING) profile_id, '{a['audience_id']}' audience_id, '{a['audience_name']}' audience_name, "
                     f"'{a['series']}' series, '{a['offer']}' offer FROM {C}.audiences.`{a['audience_id']}`")
q = " UNION ALL ".join(parts) if parts else "SELECT CAST(NULL AS STRING) profile_id, CAST(NULL AS STRING) audience_id, CAST(NULL AS STRING) audience_name, CAST(NULL AS STRING) series, CAST(NULL AS STRING) offer WHERE 1=0"
spark.sql(f"CREATE OR REPLACE TABLE {S}.gold_campaign_members COMMENT 'CustomerLake オーディエンスの対象者' AS SELECT DISTINCT *, current_timestamp() updated_at FROM ({q})")
print("campaign members:", spark.table(f"{S}.gold_campaign_members").count(), "audiences:", len(parts))

# COMMAND ----------
# MAGIC %md ## 6. レコメンド（顧客ごとに上位 5 製品）

# COMMAND ----------
tag_match = "aggregate(p.tags, 0D, (acc, t) -> acc + CASE t " + " ".join(f"WHEN '{d}' THEN coalesce(c.score_{d}, 0)" for d in DIMS) + " ELSE 0 END) / size(p.tags)"
spark.sql(f"""CREATE OR REPLACE TABLE {S}.gold_recommendations COMMENT '顧客ごとのおすすめ製品 上位 5（関心スコア×セグメント人気×予算×カテゴリ×キャンペーン）' AS
WITH cand AS (
  SELECT c.profile_id, c.segment, c.budget_band, c.next_purchase_category, c.top_interests, p.*,
         {tag_match} AS tag_match,
         coalesce(a.affinity, 0) AS seg_aff,
         CASE WHEN c.budget_band IS NULL THEN 0.5
              WHEN c.budget_band = '〜1万円' AND p.price <= 10000 THEN 1 WHEN c.budget_band = '1〜3万円' AND p.price BETWEEN 10000 AND 30000 THEN 1
              WHEN c.budget_band = '3〜10万円' AND p.price BETWEEN 30000 AND 100000 THEN 1 WHEN c.budget_band = '10万円以上' AND p.price >= 100000 THEN 1
              WHEN c.budget_band = '〜1万円' AND p.price <= 30000 THEN 0.4 WHEN c.budget_band = '1〜3万円' AND p.price <= 60000 THEN 0.4
              WHEN c.budget_band = '3〜10万円' AND p.price BETWEEN 15000 AND 250000 THEN 0.4 WHEN c.budget_band = '10万円以上' AND p.price >= 50000 THEN 0.4
              ELSE 0 END AS budget_fit,
         IF(c.next_purchase_category = p.category, 1, 0) AS cat_intent,
         cm.audience_name, cm.offer
  FROM {S}.gold_customer_360 c CROSS JOIN {S}.products p
  LEFT JOIN {S}.gold_segment_product_affinity a ON a.segment = c.segment AND a.product_id = p.product_id
  LEFT JOIN (SELECT profile_id, series, first(audience_name) audience_name, first(offer) offer FROM {S}.gold_campaign_members GROUP BY 1, 2) cm
         ON cm.profile_id = c.profile_id AND cm.series = p.series
  WHERE c.segment <> '未分類' AND NOT array_contains(c.owned_products, p.product_id)),
scored AS (
  SELECT *, round(0.5 * tag_match + 0.2 * seg_aff + 0.15 * budget_fit + 0.15 * cat_intent + IF(audience_name IS NOT NULL, 0.15, 0), 4) AS score
  FROM cand),
ranked AS (
  SELECT *, row_number() OVER (PARTITION BY profile_id ORDER BY score DESC, price) AS rank,
         row_number() OVER (PARTITION BY profile_id, series ORDER BY score DESC, price) AS series_rank FROM scored)
SELECT profile_id, rk AS rank, * EXCEPT (profile_id, rk) FROM (
SELECT profile_id, CAST(row_number() OVER (PARTITION BY profile_id ORDER BY score DESC, price) AS INT) AS rk,
       product_id, product_name, model, series, category, price, url, score,
       round(tag_match, 3) tag_match, round(seg_aff, 3) seg_aff, budget_fit, cat_intent,
       concat_ws('／',
         IF(tag_match >= 0.5, concat('関心（', array_join(transform(top_interests, x -> CASE x {LABEL_CASE} ELSE x END), '・'), '）に合う'), NULL),
         IF(seg_aff >= 0.5, concat(segment, 'で人気'), NULL),
         IF(budget_fit = 1, concat('ご予算 ', budget_band, ' に合う'), NULL),
         IF(cat_intent = 1, concat('次に欲しい：', next_purchase_category), NULL),
         IF(audience_name IS NOT NULL, concat('キャンペーン対象：', audience_name), NULL)) AS reason,
       audience_name AS campaign, offer, current_timestamp() AS updated_at
FROM ranked WHERE series_rank <= 2) WHERE rk <= 5""")

for t in ["gold_customer_360", "gold_segment_summary", "gold_topic_summary", "gold_campaign_members", "gold_recommendations", "gold_contact_profile"]:
    print(t, spark.table(f"{S}.{t}").count())
