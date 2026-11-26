"""rec/marks.json から plan.json を作る（シーン＝静止画 or 録画の区間＋読むナレーション）"""
import json
m = json.load(open("rec/marks.json"))
t = {x["name"]: x["t"] for x in m if x["name"] != "node_done"}
nd = {x["i"]: x["t"] for x in m if x["name"] == "node_done"}
V = "rec/app.webm"
def clip(id_, a, b, beats, **kw): return {"id": id_, "type": "clip", "src": V, "t0": round(a, 2), "t1": round(b, 2), "beats": beats, **kw}
def img(id_, src, beats, **kw): return {"id": id_, "type": "image", "src": src, "beats": beats, **kw}
S = [
    img("title", "cards/title.png", ["title"], zoom=[0.3, 0.5, 1.04]),
    img("arch", "cards/arch.png", ["arch"]),
    img("ch_app", "cards/ch_app.png", ["ch_app"]),
    clip("app", t["open"] - 1.5, t["picked"] - 0.2, ["app"]),
    clip("fill", t["picked"] - 0.2, t["submitted"] - 1.0, ["fill"]),
    clip("submit", t["submitted"] - 1.0, nd[1] + 1.5, ["submit"]),
    clip("cdf", nd[1] + 1.5, nd[2] + 3.0, ["cdf"], max_speed=6),
    clip("job", nd[2] + 3.0, nd[6] + 1.0, ["job"], max_speed=8),
    clip("sync", nd[6] + 1.0, nd[7] + 1.0, ["sync"], max_speed=8),
    clip("done", nd[7] + 1.0, t["customer"] - 2.5, ["done"]),
    clip("reco", t["customer"] - 2.5, t["summary"] - 1.5, ["reco"]),
    clip("summary", t["summary"] - 1.5, t["customerlake"] - 1.0, ["summary"]),
    clip("clapp", t["customerlake"] - 1.0, t["end"], ["clapp"]),
    img("ch_ws", "cards/ch_ws.png", ["ch_ws"]),
    img("idr", "../shots/idp_insights.png", ["idr"], zoom=[0.3, 0.3, 1.06]),
    img("aud", "../shots/aud1_result.png", ["aud"], zoom=[0.6, 0.5, 1.06]),
    img("jobrun", "../shots/ws_jobtl.png", ["jobrun"], zoom=[0.25, 0.2, 1.08]),
    img("synced", "../shots/ws_synced.png", ["synced"], zoom=[0.4, 0.4, 1.05]),
    img("end", "cards/end.png", ["end"], min=4),
]
json.dump({"scenes": S}, open("plan.json", "w"), ensure_ascii=False, indent=1)
print(len(S), "scenes")
