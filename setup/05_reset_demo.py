"""デモを初期状態に戻す：アプリ（channel='web'）から送った回答を Lakebase から消し、ジョブを再実行して集計を戻す。"""
import sys, json, subprocess
sys.path.insert(0, __import__("os").path.dirname(__file__)); import lb
with lb.connect() as c:
    n = c.execute("DELETE FROM survey.responses WHERE channel = 'web'").rowcount
    print("deleted web responses:", n)
job = open(__import__("os").path.join(__import__("os").path.dirname(__file__), "job_id.txt")).read().strip()
r = subprocess.run(["databricks", "jobs", "run-now", job, "--no-wait", "-p", lb.PROFILE, "-o", "json"], capture_output=True, text=True, env=lb.ENV)
print("job run:", json.loads(r.stdout)["run_id"])
