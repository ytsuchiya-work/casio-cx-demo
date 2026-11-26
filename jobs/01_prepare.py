# Databricks notebook source
# MAGIC %md
# MAGIC # 01 準備：Lakebase の変更履歴（CDF）から最新の回答を作る
# MAGIC Lakebase CDF が書き出した `lb_responses_history` / `lb_respondents_history` から、主キーごとの最新状態を取り出す。
# MAGIC 回答者は CustomerLake（Profile Agents）の名寄せ用ソース `src_survey_respondents` としても使う。

# COMMAND ----------
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "casio_cx")
C = dbutils.widgets.get("catalog"); S = dbutils.widgets.get("schema")
spark.sql(f"USE CATALOG {C}")

# COMMAND ----------
# Postgres の text[] は '{a,b}' の文字列で届くので配列に戻す
def pg_array(col):
    return f"filter(split(regexp_replace(coalesce({col}, ''), '[{{}}\"]', ''), ','), x -> x <> '')"

spark.sql(f"""
CREATE OR REPLACE TABLE {S}.silver_responses
COMMENT 'Qualtrics 回答（Lakebase CDF の履歴から主キーごとの最新を取り出したもの）' AS
WITH ranked AS (
  SELECT *, row_number() OVER (PARTITION BY response_id ORDER BY _pg_lsn DESC, _sort_by DESC) AS rn
  FROM {S}.lb_responses_history
  WHERE _pg_change_type IN ('insert', 'update_postimage', 'delete')
)
SELECT response_id, survey_id, survey_name, contact_id, submitted_at,
       CAST(nps AS INT) AS nps, CAST(satisfaction AS INT) AS satisfaction,
       {pg_array('owned_products')} AS owned_products,
       {pg_array('interests')} AS interests,
       next_purchase_category, budget_band,
       {pg_array('usage_scenes')} AS usage_scenes,
       comment, channel, raw_payload, created_at, updated_at,
       _timestamp AS lakehouse_arrived_at
FROM ranked WHERE rn = 1 AND _pg_change_type <> 'delete'
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {S}.src_survey_respondents
COMMENT 'Qualtrics 回答者（連絡先）。CustomerLake Profile Agents の名寄せソース' AS
WITH ranked AS (
  SELECT *, row_number() OVER (PARTITION BY contact_id ORDER BY _pg_lsn DESC, _sort_by DESC) AS rn
  FROM {S}.lb_respondents_history
  WHERE _pg_change_type IN ('insert', 'update_postimage', 'delete')
)
SELECT contact_id, full_name, email, nullif(phone, '') AS phone, nullif(postal_code, '') AS postal_code,
       prefecture, age_band, gender, created_at, updated_at
FROM ranked WHERE rn = 1 AND _pg_change_type <> 'delete'
""")

n = spark.sql(f"SELECT (SELECT count(*) FROM {S}.silver_responses) r, (SELECT count(*) FROM {S}.src_survey_respondents) c").first()
print(f"responses={n.r} respondents={n.c}")
dbutils.jobs.taskValues.set("responses", n.r)
