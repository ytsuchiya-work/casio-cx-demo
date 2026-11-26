"""CASIO 顧客アンケート デモ用の合成データを作る（すべて架空）。

出力（data/ 以下）:
  products.csv                 製品マスタ（casio.com/jp に掲載の型番・税込価格を 2026-11-25 に取得）
  src_casio_id_members.csv     CASIO ID 会員（Lakehouse ソース）
  src_online_store_customers.csv / online_store_orders.csv   CASIO オンラインストア（Lakehouse ソース）
  lb_respondents.csv / lb_responses.csv   Qualtrics の回答者・回答（Lakebase に投入）
  truth_xref.csv               名寄せの正解（検証用。CustomerLake には渡さない）
"""
import csv, json, random, string, datetime as dt
from pathlib import Path

random.seed(20261125)
OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- 製品マスタ
# tags: outdoor / sports / business / luxury / fashion / music / study / office / tech / wellness / family
P = [
 ("P001", "G-SHOCK GAC-2500", "GAC-2500-1AJF", "G-SHOCK", "腕時計", 20900, "fashion,sports", "/jp/watches/gshock/"),
 ("P002", "G-SHOCK GMC-2500D（メタル）", "GMC-2500D-1AJF", "G-SHOCK", "腕時計", 49500, "fashion,business", "/jp/watches/gshock/"),
 ("P003", "G-SHOCK GMW-B5000SB（フルメタル）", "GMW-B5000SB-1A2JF", "G-SHOCK", "腕時計", 110000, "luxury,tech,fashion", "/jp/watches/gshock/"),
 ("P004", "G-SHOCK DW-5600MTM", "DW-5600MTM-8JF", "G-SHOCK", "腕時計", 15950, "fashion", "/jp/watches/gshock/"),
 ("P005", "G-SHOCK GBM-2100LXB（スマホリンク）", "GBM-2100LXB-1A2JF", "G-SHOCK", "腕時計", 42900, "tech,sports,fashion", "/jp/watches/gshock/"),
 ("P006", "MR-G MRG-B5000SA（世界限定500本）", "MRG-B5000SA-2JR", "G-SHOCK", "腕時計", 880000, "luxury", "/jp/watches/new/"),
 ("P007", "BABY-G BGA-3000", "BGA-3000-7AJF", "BABY-G", "腕時計", 33000, "fashion,sports", "/jp/watches/babyg"),
 ("P008", "BABY-G BGD-565FG", "BGD-565FG-2BJF", "BABY-G", "腕時計", 10450, "fashion", "/jp/watches/babyg"),
 ("P009", "OCEANUS OCW-S7000PW", "OCW-S7000PW-7AJF", "OCEANUS", "腕時計", 236500, "luxury,business", "/jp/watches/oceanus/"),
 ("P010", "OCEANUS OCW-S400RA", "OCW-S400RA-2AJF", "OCEANUS", "腕時計", 192500, "luxury,business", "/jp/watches/oceanus/"),
 ("P011", "OCEANUS OCW-SG1000MC", "OCW-SG1000MC-1AJR", "OCEANUS", "腕時計", 748000, "luxury", "/jp/watches/oceanus/"),
 ("P012", "EDIFICE EFS-S660D", "EFS-S660D-1AJF", "EDIFICE", "腕時計", 33000, "business,sports", "/jp/watches/edifice/"),
 ("P013", "EDIFICE EFK-200D", "EFK-200D-2AJF", "EDIFICE", "腕時計", 55000, "business,luxury", "/jp/watches/edifice/"),
 ("P014", "PRO TREK PRW-B1000WM", "PRW-B1000WM-1JR", "PRO TREK", "腕時計", 140800, "outdoor,tech", "/jp/watches/protrek/"),
 ("P015", "PRO TREK PRW-61D", "PRW-61D-2JF", "PRO TREK", "腕時計", 79200, "outdoor", "/jp/watches/protrek/"),
 ("P016", "PRO TREK PRG-69", "PRG-69-1JF", "PRO TREK", "腕時計", 29700, "outdoor,sports", "/jp/watches/protrek/"),
 ("P017", "PRO TREK MANASLU PRX-8001YT", "PRX-8001YT-7JF", "PRO TREK", "腕時計", 198000, "outdoor,luxury", "/jp/watches/protrek/"),
 ("P018", "CASIO CLASSIC A1000SP", "A1000SP-7JR", "CASIO CLASSIC", "腕時計", 27500, "fashion", "/jp/watches/casio/casio-classic/"),
 ("P019", "CASIO CLASSIC A158WEMG", "A158WEMG-9JF", "CASIO CLASSIC", "腕時計", 13200, "fashion,family", "/jp/watches/casio/casio-classic/"),
 ("P020", "電子辞書 EX-word XD-SA4910（高校生）", "XD-SA4910WE", "EX-word", "電子辞書", 58300, "study,family", "/jp/exword/"),
 ("P021", "電子辞書 EX-word XD-SA6500（生活・ビジネス）", "XD-SA6500GD", "EX-word", "電子辞書", 49500, "business,study", "/jp/exword/"),
 ("P022", "電子辞書 EX-word XD-SA9000（外国語）", "XD-SA9000WE", "EX-word", "電子辞書", 40700, "study,business", "/jp/exword/"),
 ("P023", "電子辞書 EX-word XD-SX5900MED（医学）", "XD-SX5900MED", "EX-word", "電子辞書", 104500, "study", "/jp/exword/"),
 ("P024", "電子辞書 EX-word XD-C400（コンパクト）", "XD-C400GD", "EX-word", "電子辞書", 19800, "study,office", "/jp/exword/"),
 ("P025", "関数電卓 ClassWiz fx-JP900CW", "fx-JP900CWS", "ClassWiz", "電卓", 7920, "study", "/jp/scientific-calculators/"),
 ("P026", "グラフ関数電卓 fx-CG100", "fx-CG100", "ClassWiz", "電卓", 30800, "study,tech", "/jp/scientific-calculators/"),
 ("P027", "プログラム関数電卓 fx-5800P", "fx-5800P", "関数電卓", "電卓", 15400, "office,tech", "/jp/scientific-calculators/"),
 ("P028", "電子ピアノ Privia PX-S1100", "PX-S1100BK", "Privia", "電子楽器", 69300, "music", "/jp/electronic-musical-instruments/privia/"),
 ("P029", "キーボード Casiotone CT-S1000V", "CT-S1000V", "Casiotone", "電子楽器", 55000, "music,tech", "/jp/electronic-musical-instruments/casiotone/"),
 ("P030", "キーボード Casiotone CT-S1", "CT-S1BK", "Casiotone", "電子楽器", 30800, "music,fashion", "/jp/electronic-musical-instruments/casiotone/"),
 ("P031", "キーボード Casiotone CT-S400", "CT-S400", "Casiotone", "電子楽器", 30800, "music,family", "/jp/electronic-musical-instruments/casiotone/"),
 ("P032", "ラベルライター ネームランド KL-SP10", "KL-SP10", "ネームランド", "ラベルライター", 7700, "office,family", "/jp/label-writer/"),
 ("P033", "ラベルライター ネームランド KL-SP100", "KL-SP100", "ネームランド", "ラベルライター", 13200, "office", "/jp/label-writer/"),
 ("P034", "AIペットロボット Moflin PE-M11", "PE-M11GD", "Moflin", "AIペット", 64900, "wellness,family,tech", "/jp/moflin/products/"),
 ("P035", "AIペットロボット Moflin PE-M10", "PE-M10GD", "Moflin", "AIペット", 59400, "wellness,family", "/jp/moflin/products/"),
]
PRODUCTS = [dict(product_id=a, product_name=b, model=c, series=d, category=e, price=f, tags=g,
                 url="https://www.casio.com" + h) for a, b, c, d, e, f, g, h in P]
PBY = {p["product_id"]: p for p in PRODUCTS}
DIMS = ["outdoor", "sports", "business", "luxury", "fashion", "music", "study", "office", "tech", "wellness", "family"]

# ---------------------------------------------------------------- ペルソナ（真の嗜好）
PERSONAS = {
    "outdoor":  dict(w=0.18, dims={"outdoor": .9, "sports": .6, "tech": .4}, series=["PRO TREK", "G-SHOCK"], age=(28, 65)),
    "business": dict(w=0.17, dims={"business": .9, "luxury": .6, "tech": .3}, series=["OCEANUS", "EDIFICE", "EX-word"], age=(30, 62)),
    "fashion":  dict(w=0.20, dims={"fashion": .9, "sports": .4, "tech": .3}, series=["G-SHOCK", "BABY-G", "CASIO CLASSIC"], age=(16, 40)),
    "music":    dict(w=0.13, dims={"music": .9, "family": .4, "tech": .3}, series=["Privia", "Casiotone"], age=(10, 60)),
    "study":    dict(w=0.17, dims={"study": .9, "office": .5, "family": .4}, series=["EX-word", "ClassWiz", "ネームランド"], age=(15, 55)),
    "wellness": dict(w=0.15, dims={"wellness": .9, "family": .6, "fashion": .2}, series=["Moflin", "CASIO CLASSIC", "ネームランド"], age=(35, 80)),
}

SURN = [("佐藤","サトウ"),("鈴木","スズキ"),("高橋","タカハシ"),("田中","タナカ"),("伊藤","イトウ"),("渡辺","ワタナベ"),("山本","ヤマモト"),("中村","ナカムラ"),
        ("小林","コバヤシ"),("加藤","カトウ"),("吉田","ヨシダ"),("山田","ヤマダ"),("佐々木","ササキ"),("山口","ヤマグチ"),("松本","マツモト"),("井上","イノウエ"),
        ("木村","キムラ"),("林","ハヤシ"),("斎藤","サイトウ"),("清水","シミズ"),("山崎","ヤマザキ"),("森","モリ"),("池田","イケダ"),("橋本","ハシモト"),
        ("阿部","アベ"),("石川","イシカワ"),("山下","ヤマシタ"),("中島","ナカジマ"),("石井","イシイ"),("小川","オガワ"),("前田","マエダ"),("岡田","オカダ"),
        ("長谷川","ハセガワ"),("藤田","フジタ"),("後藤","ゴトウ"),("近藤","コンドウ"),("村上","ムラカミ"),("遠藤","エンドウ"),("青木","アオキ"),("坂本","サカモト"),
        ("斉藤","サイトウ"),("福田","フクダ"),("太田","オオタ"),("西村","ニシムラ"),("藤井","フジイ"),("金子","カネコ"),("岡本","オカモト"),("藤原","フジワラ"),
        ("中野","ナカノ"),("三浦","ミウラ"),("原田","ハラダ"),("中川","ナカガワ"),("松田","マツダ"),("竹内","タケウチ"),("小野","オノ"),("田村","タムラ")]
GIVEN_M = [("翔太","ショウタ"),("大輔","ダイスケ"),("健太","ケンタ"),("拓也","タクヤ"),("直樹","ナオキ"),("和也","カズヤ"),("誠","マコト"),("亮","リョウ"),
           ("隆","タカシ"),("浩二","コウジ"),("悠真","ユウマ"),("蓮","レン"),("湊","ミナト"),("陽翔","ハルト"),("樹","イツキ"),("大和","ヤマト"),
           ("健一","ケンイチ"),("修","オサム"),("剛","ツヨシ"),("裕太","ユウタ"),("達也","タツヤ"),("圭","ケイ"),("慎也","シンヤ"),("学","マナブ")]
GIVEN_F = [("陽菜","ヒナ"),("結衣","ユイ"),("美咲","ミサキ"),("さくら","サクラ"),("葵","アオイ"),("彩","アヤ"),("真由美","マユミ"),("裕子","ユウコ"),
           ("恵","メグミ"),("花子","ハナコ"),("由美","ユミ"),("愛","アイ"),("七海","ナナミ"),("芽依","メイ"),("凛","リン"),("紬","ツムギ"),
           ("智子","トモコ"),("久美子","クミコ"),("明美","アケミ"),("麻衣","マイ"),("莉子","リコ"),("千尋","チヒロ"),("友美","トモミ"),("洋子","ヨウコ")]
ROMA = {}  # kana -> romaji（メール用）
KANA2ROMA = {"ア":"a","イ":"i","ウ":"u","エ":"e","オ":"o","カ":"ka","キ":"ki","ク":"ku","ケ":"ke","コ":"ko","サ":"sa","シ":"shi","ス":"su","セ":"se","ソ":"so",
 "タ":"ta","チ":"chi","ツ":"tsu","テ":"te","ト":"to","ナ":"na","ニ":"ni","ヌ":"nu","ネ":"ne","ノ":"no","ハ":"ha","ヒ":"hi","フ":"fu","ヘ":"he","ホ":"ho",
 "マ":"ma","ミ":"mi","ム":"mu","メ":"me","モ":"mo","ヤ":"ya","ユ":"yu","ヨ":"yo","ラ":"ra","リ":"ri","ル":"ru","レ":"re","ロ":"ro","ワ":"wa","ン":"n",
 "ガ":"ga","ギ":"gi","グ":"gu","ゲ":"ge","ゴ":"go","ザ":"za","ジ":"ji","ズ":"zu","ゼ":"ze","ゾ":"zo","ダ":"da","ヂ":"ji","ヅ":"zu","デ":"de","ド":"do",
 "バ":"ba","ビ":"bi","ブ":"bu","ベ":"be","ボ":"bo","パ":"pa","ピ":"pi","プ":"pu","ペ":"pe","ポ":"po"}
def roma(k):
    s, i = "", 0
    while i < len(k):
        c = k[i]
        if i + 1 < len(k) and k[i+1] in "ャュョ":
            base = KANA2ROMA.get(c, "")
            s += (base[:-1] if base.endswith("i") else base) + {"ャ":"ya","ュ":"yu","ョ":"yo"}[k[i+1]]
            if base in ("shi", "chi", "ji"): s = s[:-2] + {"ャ":"a","ュ":"u","ョ":"o"}[k[i+1]]
            i += 2; continue
        if c == "ッ": i += 1; nxt = KANA2ROMA.get(k[i], "t") if i < len(k) else "t"; s += nxt[0]; continue
        if c == "ー": i += 1; continue
        s += KANA2ROMA.get(c, ""); i += 1
    return s

PLACES = [("東京都","渋谷区","150-0001"),("東京都","世田谷区","154-0012"),("東京都","練馬区","176-0001"),("東京都","八王子市","192-0081"),
          ("神奈川県","横浜市港北区","222-0033"),("神奈川県","川崎市中原区","211-0004"),("神奈川県","藤沢市","251-0052"),("埼玉県","さいたま市浦和区","330-0062"),
          ("千葉県","船橋市","273-0005"),("大阪府","大阪市北区","530-0001"),("大阪府","吹田市","564-0027"),("京都府","京都市左京区","606-8203"),
          ("兵庫県","神戸市中央区","650-0021"),("愛知県","名古屋市中区","460-0008"),("福岡県","福岡市博多区","812-0011"),("北海道","札幌市中央区","060-0001"),
          ("宮城県","仙台市青葉区","980-0021"),("広島県","広島市中区","730-0011"),("長野県","松本市","390-0811"),("静岡県","静岡市葵区","420-0853")]
TOWNS = ["本町","中央","旭町","栄町","緑が丘","桜木町","若葉","東町","西町","南町","北町","泉","青葉台","富士見"]
DOMAINS = ["gmail.com", "yahoo.co.jp", "icloud.com", "docomo.ne.jp", "ezweb.ne.jp", "outlook.jp"]
WORK_DOM = ["example-corp.co.jp", "sample-shoji.jp", "demo-ind.co.jp"]

_USED = set()
def uniq(f):
    while True:
        v = f()
        if v not in _USED: _USED.add(v); return v
def rid(prefix, n=10):
    return uniq(lambda: prefix + "".join(random.choices(string.ascii_letters + string.digits, k=n)))

N_PERSON = 3000
NOW = dt.datetime(2026, 11, 20, 12, 0)
persons = []
pkeys = list(PERSONAS); pw = [PERSONAS[k]["w"] for k in pkeys]
for i in range(N_PERSON):
    per = random.choices(pkeys, pw)[0]
    sec = random.choice([k for k in pkeys if k != per]) if random.random() < 0.55 else None
    female = random.random() < 0.5
    sn, snk = random.choice(SURN); gn, gnk = random.choice(GIVEN_F if female else GIVEN_M)
    a0, a1 = PERSONAS[per]["age"]; age = random.randint(a0, a1)
    pref, city, zipc = random.choice(PLACES)
    zipc = zipc[:4] + f"{random.randint(0, 999):03d}"
    addr = f"{random.choice(TOWNS)}{random.randint(1, 5)}-{random.randint(1, 30)}-{random.randint(1, 20)}"
    em_local = roma(gnk) + random.choice([".", "_", ""]) + roma(snk) + (str(random.randint(1, 99)) if random.random() < .5 else "")
    persons.append(dict(pid=f"T{i:05d}", persona=per, second=sec, female=female, sn=sn, snk=snk, gn=gn, gnk=gnk, age=age,
                        pref=pref, city=city, zip=zipc, addr=addr,
                        email=f"{em_local}@{random.choice(DOMAINS)}",
                        work_email=f"{roma(snk)}.{roma(gnk)[0]}@{random.choice(WORK_DOM)}",
                        phone=f"0{random.choice([7, 8, 9])}0-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                        birth=(dt.date(2026, 4, 1) - dt.timedelta(days=age * 365 + random.randint(0, 364))).isoformat()))

def affinity(p, prod):
    d = dict(PERSONAS[p["persona"]]["dims"])
    if p["second"]:
        for k, v in PERSONAS[p["second"]]["dims"].items(): d[k] = max(d.get(k, 0), v * .6)
    tags = prod["tags"].split(",")
    s = sum(d.get(t, 0) for t in tags) / len(tags)
    if prod["series"] in PERSONAS[p["persona"]]["series"]: s += .5
    if prod["price"] > 300000: s *= .25 if p["persona"] != "business" else .5
    if prod["category"] == "電子辞書" and prod["product_id"] == "P020" and not (15 <= p["age"] <= 19 or 40 <= p["age"] <= 55): s *= .3
    return s

def pick_products(p, k):
    sc = [(affinity(p, pr) + random.random() * .35, pr["product_id"]) for pr in PRODUCTS]
    sc.sort(reverse=True)
    return [x[1] for x in sc[:k]]

truth = []
def w(name, rows, cols):
    with open(OUT / name, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(rows)
    print(f"{name}: {len(rows)}")

# ---------------------------------------------------------------- CASIO ID 会員
members = []
for p in persons:
    if random.random() < .82:
        mid = uniq(lambda: f"CID{random.randint(10**7, 10**8 - 1)}")
        members.append(dict(member_id=mid, last_name=p["sn"], first_name=p["gn"], last_name_kana=p["snk"], first_name_kana=p["gnk"],
                            email=p["email"], phone=p["phone"], postal_code=p["zip"], prefecture=p["pref"], city=p["city"], address_line=p["addr"],
                            birth_date=p["birth"], gender="女性" if p["female"] else "男性",
                            registered_at=(NOW - dt.timedelta(days=random.randint(30, 2500))).strftime("%Y-%m-%d %H:%M:%S"),
                            newsletter_optin=random.random() < .6))
        truth.append(dict(source="casio_id_members", record_id=mid, person_id=p["pid"]))
        p["member_id"] = mid
w("src_casio_id_members.csv", members, list(members[0]))

# ---------------------------------------------------------------- オンラインストア
store, orders = [], []
for p in persons:
    if random.random() < .45:
        cno = uniq(lambda: f"OS{random.randint(10**6, 10**7 - 1)}")
        name = random.choice([f"{p['sn']} {p['gn']}", f"{p['sn']}{p['gn']}", f"{p['sn']}　{p['gn']}"])
        email = p["email"] if random.random() < .65 else (p["work_email"] if random.random() < .6 else p["email"].upper())
        tel = p["phone"].replace("-", "") if random.random() < .7 else p["phone"]
        store.append(dict(customer_no=cno, full_name=name, full_name_kana=f"{p['snk']} {p['gnk']}", email=email, tel=tel,
                          zip=p["zip"].replace("-", ""), address=f"{p['pref']}{p['city']}{p['addr']}",
                          created_at=(NOW - dt.timedelta(days=random.randint(10, 1800))).strftime("%Y-%m-%d %H:%M:%S")))
        truth.append(dict(source="online_store_customers", record_id=cno, person_id=p["pid"]))
        p["store_no"] = cno
        for pid in pick_products(p, random.choice([1, 1, 2, 2, 3, 4])):
            if random.random() < .75:
                od = NOW - dt.timedelta(days=random.randint(5, 900))
                orders.append(dict(order_id=f"ORD{random.randint(10**8, 10**9 - 1)}", customer_no=cno, product_id=pid, quantity=1,
                                   amount=PBY[pid]["price"], order_date=od.strftime("%Y-%m-%d %H:%M:%S")))
                p.setdefault("owned", set()).add(pid)
w("src_online_store_customers.csv", store, list(store[0]))
w("online_store_orders.csv", orders, list(orders[0]))

# ---------------------------------------------------------------- Qualtrics 回答者・回答（Lakebase）
SURVEYS = [
    ("SV_8dWatchSat2026", "腕時計 ご購入者満足度アンケート"),
    ("SV_3fLifeInterest", "ライフスタイルと製品への関心アンケート"),
    ("SV_6aLearnMusic26", "学び・音楽製品アンケート"),
]
SCENES = {"outdoor": ["登山", "キャンプ", "釣り", "トレイルラン"], "sports": ["ランニング", "ジム", "サーフィン"],
          "business": ["通勤", "商談", "出張"], "luxury": ["フォーマル", "記念日"], "fashion": ["街歩き", "コーデのアクセント"],
          "music": ["ピアノの練習", "弾き語り", "作曲"], "study": ["受験勉強", "語学学習", "資格の勉強"], "office": ["事務作業", "書類整理"],
          "wellness": ["リラックスタイム", "ひとり時間"], "family": ["家族へのプレゼント", "子どもの入学祝い"], "tech": ["スマホ連携"]}
CAT_OF_PERSONA = {"outdoor": "腕時計", "business": "腕時計", "fashion": "腕時計", "music": "電子楽器", "study": "電子辞書", "wellness": "AIペット"}
GOOD = {"outdoor": ["方位計と高度計が山で本当に頼りになる", "タフソーラーで電池切れの心配がない", "グローブをしたままでもボタンが押しやすい"],
        "sports": ["ランニング中でも表示が見やすい", "軽くて運動の邪魔にならない"],
        "business": ["スーツに合わせても上品に見える", "電波ソーラーで時刻合わせが要らず出張に便利", "チタンで軽く一日中着けていても疲れない"],
        "luxury": ["仕上げが美しく所有する満足感が高い", "ブルーの文字盤が想像以上にきれい"],
        "fashion": ["どんな服にも合わせやすいデザイン", "色違いで集めたくなる", "友達にもかっこいいと言われた"],
        "music": ["鍵盤のタッチがピアノに近い", "スピーカーの音がきれいで練習が楽しい", "軽くて部屋の中で移動しやすい"],
        "study": ["収録辞書が多く調べ物がすぐ終わる", "画面が見やすく長時間使っても疲れにくい", "関数電卓の自然表示で計算ミスが減った"],
        "office": ["ラベル作りがスマホから簡単にできる"], "tech": ["スマホとの連携が便利", "アプリで設定を変えられるのが良い"],
        "wellness": ["Moflin のしぐさに毎日癒やされている", "鳴き声が自然で家族みんなが気に入っている"],
        "family": ["プレゼントしたらとても喜ばれた"]}
BAD = ["価格がもう少し安いと嬉しい", "バンドの調整が分かりにくかった", "取扱説明書が分かりにくい", "もう少し軽いと嬉しい",
       "アプリの接続が時々切れる", "店頭で実物を見られる場所が少ない", "サイズが少し大きく感じる", "色の選択肢がもっと欲しい",
       "電池の持ちが思ったより短い", "配送が少し遅かった"]
WANT = {"outdoor": ["次は登山用にもっと高機能なモデルが欲しい", "キャンプ用に軽いモデルを探している"],
        "business": ["仕事用にもう一本、上質なモデルを検討している", "出張が多いのでワールドタイム機能を重視したい"],
        "fashion": ["限定カラーやコラボモデルの情報が欲しい", "ペアで使えるモデルを探している"],
        "music": ["子どもの練習用に電子ピアノを検討中", "持ち運べるキーボードが欲しい"],
        "study": ["新学期に子どもの電子辞書を買い替えたい", "資格試験用に関数電卓を探している"],
        "wellness": ["親へのプレゼントに Moflin を考えている", "癒やし系の製品をもっと知りたい"]}
BUDGET = ["〜1万円", "1〜3万円", "3〜10万円", "10万円以上"]
INTEREST_LABEL = {"outdoor": "アウトドア", "sports": "スポーツ", "business": "ビジネス", "luxury": "上質・高級", "fashion": "ファッション",
                  "music": "音楽", "study": "学び", "office": "事務・実務", "tech": "スマート連携", "wellness": "癒やし", "family": "家族・ギフト"}

respondents, responses = [], []
for p in persons:
    if random.random() >= .72: continue
    cid = rid("CNT_", 10)
    # 回答者情報は Qualtrics の連絡先リストから。表記ゆれあり
    name_full = random.choice([f"{p['sn']} {p['gn']}", f"{p['sn']}{p['gn']}", f"{p['snk']} {p['gnk']}"])
    email = p["email"] if random.random() < .8 else (p["work_email"] if random.random() < .5 else p["email"].replace("@", "+survey@"))
    phone = (p["phone"] if random.random() < .5 else p["phone"].replace("-", "")) if random.random() < .75 else ""
    respondents.append(dict(contact_id=cid, full_name=name_full, email=email, phone=phone, postal_code=p["zip"] if random.random() < .7 else "",
                            prefecture=p["pref"], age_band=f"{p['age'] // 10 * 10}代", gender="女性" if p["female"] else "男性",
                            created_at=(NOW - dt.timedelta(days=random.randint(200, 900))).strftime("%Y-%m-%d %H:%M:%S")))
    truth.append(dict(source="survey_respondents", record_id=cid, person_id=p["pid"]))
    n_resp = random.choices([1, 2, 3, 4, 5, 6, 8, 10, 14], [8, 14, 18, 18, 14, 11, 8, 6, 3])[0]
    owned = set(p.get("owned", set())) | set(pick_products(p, random.choice([0, 1, 1, 2])))
    for k in range(n_resp):
        ts = NOW - dt.timedelta(days=random.randint(1, 720), minutes=random.randint(0, 1440))
        per = p["persona"] if (random.random() < .78 or not p["second"]) else p["second"]
        dims = sorted(PERSONAS[per]["dims"], key=lambda d: -PERSONAS[per]["dims"][d])
        interests = dims[:random.choice([1, 2, 2, 3])]
        if random.random() < .15: interests.append(random.choice(DIMS))
        interests = list(dict.fromkeys(interests))
        scene = random.sample(sum([SCENES.get(d, []) for d in interests], []) or ["日常使い"], k=1)
        sat = max(1, min(5, round(random.gauss(4.0 if per != "fashion" else 3.8, .8))))
        nps = max(0, min(10, round(random.gauss({5: 9.2, 4: 7.8, 3: 6.0, 2: 4, 1: 2}[sat], 1.1))))
        sv = SURVEYS[0] if CAT_OF_PERSONA[per] == "腕時計" and random.random() < .6 else (SURVEYS[2] if per in ("music", "study") and random.random() < .6 else SURVEYS[1])
        own = [x for x in owned if random.random() < .7][:3]
        own_match = [x for x in own if PBY[x]["series"] in PERSONAS[per]["series"]]
        parts = []
        if own_match:
            parts.append(f"{scene[0]}で{PBY[own_match[0]]['series']}を使っています。")
        else:
            parts.append(f"{scene[0]}に使える{random.choice(PERSONAS[per]['series'])}を探しています。")
        parts.append(random.choice(GOOD.get(interests[0], GOOD[per])) + "。")
        if sat <= 3 or random.random() < .45: parts.append(random.choice(BAD) + "。")
        if random.random() < .6: parts.append(random.choice(WANT[per]) + "。")
        comment = "".join(parts)
        bud = random.choices(BUDGET, {"business": [1, 2, 4, 5], "outdoor": [1, 3, 5, 3], "fashion": [3, 6, 3, 1], "music": [1, 2, 6, 1],
                                      "study": [3, 4, 4, 1], "wellness": [1, 2, 6, 1]}[per])[0]
        rid_ = rid("R_", 15)
        payload = {"responseId": rid_, "surveyId": sv[0], "contactId": cid, "recordedDate": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "values": {"QID1_NPS": nps, "QID2_SAT": sat, "QID3_OWNED": own, "QID4_INTEREST": interests,
                              "QID5_NEXT": CAT_OF_PERSONA[per], "QID6_BUDGET": bud, "QID7_SCENE": scene, "QID8_TEXT": comment},
                   "distributionChannel": random.choice(["email", "anonymous", "app", "qr"])}
        responses.append(dict(response_id=rid_, survey_id=sv[0], survey_name=sv[1], contact_id=cid, submitted_at=ts.strftime("%Y-%m-%d %H:%M:%S"),
                              nps=nps, satisfaction=sat, owned_products="{" + ",".join(own) + "}", interests="{" + ",".join(interests) + "}",
                              next_purchase_category=CAT_OF_PERSONA[per], budget_band=bud, usage_scenes="{" + ",".join(scene) + "}",
                              comment=comment, channel=payload["distributionChannel"], raw_payload=json.dumps(payload, ensure_ascii=False)))
w("lb_respondents.csv", respondents, list(respondents[0]))
w("lb_responses.csv", responses, list(responses[0]))
w("truth_xref.csv", truth, ["source", "record_id", "person_id"])
w("products.csv", PRODUCTS, list(PRODUCTS[0]))
w("persons_truth.csv", [dict(person_id=p["pid"], persona=p["persona"], second=p["second"] or "") for p in persons], ["person_id", "persona", "second"])
json.dump({"surveys": SURVEYS, "interest_label": INTEREST_LABEL, "scenes": SCENES, "budget": BUDGET}, open(OUT / "survey_meta.json", "w"), ensure_ascii=False, indent=1)
print("distinct comments:", len({r["comment"] for r in responses}))
