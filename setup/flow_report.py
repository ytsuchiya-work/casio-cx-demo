"""直近のフローの各段の所要時間を表示。usage: python flow_report.py [flowId]"""
import sys, requests
fl = requests.get("http://localhost:8080/api/flows").json()
f = next((x for x in fl if len(sys.argv) < 2 or x["flowId"] == sys.argv[1]), None)
t0 = f["startedAt"]
last = {}
for e in f["events"]: last[e["step"]] = e
for k, e in last.items():
    s = (e.get("startAt") or e["at"]) - t0; d = e["at"] - (e.get("startAt") or e["at"])
    print(f"{k:14s} {e['status']:8s} start={s/1000:7.1f}s dur={d/1000:6.1f}s  {e.get('detail') or ''}")
if f.get("after"): print("after:", [x["product_name"] for x in f["after"]])
