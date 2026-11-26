# Databricks notebook source
# MAGIC %md
# MAGIC # 04 リバース ETL：集計テーブルを Lakebase に反映（同期テーブル・LTAP Direct Writes）
# MAGIC 同期テーブル（Snapshot モード、LTAP Direct Writes を有効にして作成）の更新を開始し、全テーブルの反映を待つ。
# MAGIC LTAP Direct Writes は Lakebase のコンピュートを通さずストレージ層へ直接書き込むので、大量の行をまるごと入れ替えてもアプリの問い合わせと競合しない。

# COMMAND ----------
import time
from databricks.sdk import WorkspaceClient
dbutils.widgets.text("synced_tables", "")
NAMES = [x.strip() for x in dbutils.widgets.get("synced_tables").split(",") if x.strip()]
w = WorkspaceClient()

def pipeline_of(name):
    st = w.api_client.do("GET", f"/api/2.0/postgres/synced_tables/{name}")
    return st["status"].get("pipeline_id")

started = {}
for n in NAMES:
    pid = pipeline_of(n)
    for attempt in range(30):
        try:
            u = w.pipelines.start_update(pipeline_id=pid)
            started[n] = (pid, u.update_id, time.time()); print("start", n, pid, u.update_id); break
        except Exception as e:  # 前の更新が動いている時は待つ
            print("wait", n, str(e)[:120]); time.sleep(5)

done = {}
while len(done) < len(started):
    for n, (pid, uid, t0) in started.items():
        if n in done: continue
        st = w.pipelines.get_update(pipeline_id=pid, update_id=uid).update.state.value
        if st in ("COMPLETED", "FAILED", "CANCELED"):
            done[n] = (st, round(time.time() - t0, 1)); print(n, st, done[n][1], "s")
    time.sleep(3)
bad = [n for n, (st, _) in done.items() if st != "COMPLETED"]
if bad: raise Exception(f"sync failed: {bad}")
dbutils.jobs.taskValues.set("synced", {n: v[1] for n, v in done.items()})
