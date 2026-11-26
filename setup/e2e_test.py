"""アプリの API で E2E を試す：顧客の回答を送信し、SSE で各段の完了を待って所要時間を出す。usage: python e2e_test.py <profile_id>"""
import sys, json, time, requests
import os
B = os.environ.get("APP_URL", "http://localhost:8080")
H = {"Authorization": "Bearer " + os.environ["APP_TOKEN"]} if os.environ.get("APP_TOKEN") else {}
pid = sys.argv[1]
d = requests.get(f"{B}/api/customers/{pid}", headers=H).json()
r = d["respondent"]
print("customer:", d["customer"]["display_name"], d["customer"]["segment"], "before:", [x["product_name"] for x in d["recommendations"]][:3])
body = {"surveyId": "SV_3fLifeInterest", "surveyName": "ライフスタイルと製品への関心アンケート", "contactId": r["contact_id"], "nps": 9, "satisfaction": 5,
        "interests": ["outdoor", "sports", "tech"], "scenes": ["登山", "キャンプ"], "next": "腕時計", "budget": "10万円以上", "owned": [],
        "comment": "最近登山を始めました。山で方位や高度がすぐ分かる、丈夫な腕時計が欲しいです。スマホと連携してルートを記録できると嬉しい。",
        "contact": {"fullName": r["full_name"], "email": r["email"], "phone": r["phone"], "postalCode": r["postal_code"], "prefecture": r["prefecture"], "ageBand": r["age_band"], "gender": r["gender"]}}
t0 = time.time()
res = requests.post(f"{B}/api/survey/submit", json=body, headers=H).json(); fid = res["flowId"]; print("flow", fid, "accepted in", round(time.time() - t0, 2), "s")
with requests.get(f"{B}/api/events", stream=True, timeout=1200, headers=H) as s:
    s.encoding = "utf-8"
    ev = None
    for line in s.iter_lines(decode_unicode=True):
        if line.startswith("event:"): ev = line[6:].strip()
        elif line.startswith("data:") and ev == "step":
            e = json.loads(line[5:])
            if e["flowId"] != fid: continue
            dur = (e["at"] - e["startAt"]) / 1000 if e.get("startAt") else None
            print(f"{time.time() - t0:7.1f}s  {e['step']:14s} {e['status']:8s} {'' if dur is None else f'{dur:.1f}s'}  {e.get('detail') or ''}")
            if e["step"] == "app" and e["status"] in ("done", "error"):
                if e.get("data"): print("after:", [x["product_name"] for x in e["data"]["after"]][:5])
                break
