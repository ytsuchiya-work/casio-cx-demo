# Databricks notebook source
# MAGIC %md
# MAGIC # 02 AI 分類：自由記述を話題・感情・関心タグに分ける
# MAGIC まだ分類していない回答だけを、Unity Catalog のモデルサービス（AI Gateway 経由の Claude）に 25 件ずつ渡して分類する。
# MAGIC 結果は `response_labels` に MERGE する（何度実行しても同じ結果）。

# COMMAND ----------
import json, re, time, requests
from concurrent.futures import ThreadPoolExecutor
from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "casio_cx")
dbutils.widgets.text("model_service", "main.casio_cx.survey_classifier")
C = dbutils.widgets.get("catalog"); S = dbutils.widgets.get("schema"); MS = dbutils.widgets.get("model_service")
spark.sql(f"USE CATALOG {C}")

TOPICS = ["デザイン", "機能・性能", "装着感・重さ", "耐久性・タフさ", "電池・充電", "スマホ連携", "価格", "説明書・サポート",
          "購入・配送", "音・鍵盤", "辞書・学習", "癒やし", "ギフト"]
TAGS = ["outdoor", "sports", "business", "luxury", "fashion", "music", "study", "office", "tech", "wellness", "family"]

spark.sql(f"""CREATE TABLE IF NOT EXISTS {S}.response_labels (
  response_id STRING, comment_hash STRING, sentiment STRING, topics ARRAY<STRING>, interest_tags ARRAY<STRING>,
  purchase_intent BOOLEAN, summary STRING, model STRING, labeled_at TIMESTAMP)
COMMENT 'アンケート自由記述の AI 分類結果（モデルサービス経由）'""")

todo = spark.sql(f"""
SELECT r.response_id, r.comment, sha2(coalesce(r.comment, ''), 256) AS h
FROM {S}.silver_responses r LEFT JOIN {S}.response_labels l ON l.response_id = r.response_id
WHERE r.comment IS NOT NULL AND (l.response_id IS NULL OR l.comment_hash <> sha2(r.comment, 256))
""").collect()
print("to classify:", len(todo))

# COMMAND ----------
w = WorkspaceClient()
URL = f"{w.config.host}/ai-gateway/mlflow/v1/chat/completions"
PROMPT = f"""あなたは家電メーカーの顧客アンケート分析者です。各コメントを分類し、1行1件で「番号|感情|話題|関心|購入意向|要約」だけを返してください。説明や見出しは不要です。
感情: p=好意的 u=中立 n=否定的
話題（1〜3個の番号をカンマ区切り）: {" ".join(f"{i}={t}" for i, t in enumerate(TOPICS))}
関心（1〜3個の番号をカンマ区切り）: {" ".join(f"{i}={t}" for i, t in enumerate(TAGS))}
（関心の意味: outdoor=登山・キャンプ等, sports=運動, business=仕事, luxury=上質・高級, fashion=服装・デザイン, music=楽器, study=学習・資格, office=事務, tech=スマホ連携・多機能, wellness=癒やし・健康, family=家族・贈り物）
購入意向: 1=あり 0=なし。要約: 20字以内
例: 3|p|1,4|0,8|1|山で方位計が便利、軽量化を希望"""
SENT = {"p": "positive", "u": "neutral", "n": "negative"}

def text_of(msg):
    c = msg.get("content")
    if isinstance(c, list):
        return "".join(b.get("text", "") for b in c if b.get("type") == "text")
    return c or ""

def idx(s, vocab):
    out = []
    for x in re.split(r"[,、\s]+", s.strip()):
        if x.isdigit() and int(x) < len(vocab): out.append(vocab[int(x)])
    return list(dict.fromkeys(out))[:3]

def classify(batch):
    body = {"model": MS, "max_tokens": 2500,
            "messages": [{"role": "system", "content": PROMPT},
                         {"role": "user", "content": "\n".join(f"{i}. {r['comment']}" for i, r in enumerate(batch))}]}
    for attempt in range(10):
        try:
            res = requests.post(URL, json=body, headers=w.config.authenticate(), timeout=180)
            if res.status_code == 429:  # 出力トークン/分の上限。待ってから再試行
                time.sleep(15 + 10 * attempt); continue
            res.raise_for_status()
            out = []
            for line in text_of(res.json()["choices"][0]["message"]).splitlines():
                p = [x.strip() for x in line.split("|")]
                if len(p) < 5 or not p[0].isdigit() or int(p[0]) >= len(batch): continue
                r = batch[int(p[0])]
                out.append((r["response_id"], r["h"], SENT.get(p[1], "neutral"), idx(p[2], TOPICS), idx(p[3], TAGS), p[4] == "1", (p[5] if len(p) > 5 else "")[:40]))
            if out: return out
        except Exception as e:
            print("retry", attempt, str(e)[:160]); time.sleep(5 * (attempt + 1))
    return []

def save(results):
    if not results: return
    df = spark.createDataFrame(results, "response_id string, comment_hash string, sentiment string, topics array<string>, interest_tags array<string>, purchase_intent boolean, summary string")
    df.createOrReplaceTempView("new_labels")
    spark.sql(f"""MERGE INTO {S}.response_labels t USING (SELECT *, '{MS}' AS model, current_timestamp() AS labeled_at FROM new_labels) s
                  ON t.response_id = s.response_id
                  WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *""")

rows = [r.asDict() for r in todo]
batches = [rows[i:i + 25] for i in range(0, len(rows), 25)]
t0 = time.time(); total = 0; buf = []
with ThreadPoolExecutor(max_workers=6) as ex:
    for k, out in enumerate(ex.map(classify, batches)):
        buf += out
        if len(buf) >= 1000: save(buf); total += len(buf); buf = []; print(f"{k + 1}/{len(batches)} batches, {total} saved, {time.time() - t0:.0f}s")
save(buf); total += len(buf)
print(f"labeled {total}/{len(rows)} in {time.time() - t0:.1f}s")
if rows and total < len(rows) * 0.9:
    print(f"WARNING: 未分類が残っている（{len(rows) - total} 件）。次回の実行で続きから分類する")
dbutils.jobs.taskValues.set("labeled", total)
