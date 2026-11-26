import { useEffect, useState } from "react";
import { get, post, DIMS, DIM_LABEL, SCENES, SURVEYS, CATEGORIES, BUDGETS } from "./api";

interface Form { surveyId: string; nps: number; satisfaction: number; interests: string[]; scenes: string[]; next: string; budget: string; owned: string[]; comment: string; }
const EMPTY: Form = { surveyId: SURVEYS[1].id, nps: 8, satisfaction: 4, interests: [], scenes: [], next: "腕時計", budget: "3〜10万円", owned: [], comment: "" };
const PRESETS: { label: string; f: Partial<Form> }[] = [
  { label: "登山を始めた", f: { surveyId: SURVEYS[1].id, nps: 9, satisfaction: 5, interests: ["outdoor", "sports", "tech"], scenes: ["登山", "キャンプ"], next: "腕時計", budget: "10万円以上",
      comment: "最近登山を始めました。山で方位や高度がすぐ分かる、丈夫な腕時計が欲しいです。スマホと連携してルートを記録できると嬉しい。" } },
  { label: "子どもが高校に入学", f: { surveyId: SURVEYS[2].id, nps: 8, satisfaction: 4, interests: ["study", "family"], scenes: ["受験勉強", "家族へのプレゼント"], next: "電子辞書", budget: "3〜10万円",
      comment: "来春に子どもが高校に入学するので、授業で使える電子辞書を探しています。画面が見やすく長く使えるものがいいです。" } },
  { label: "ピアノを再開したい", f: { surveyId: SURVEYS[2].id, nps: 7, satisfaction: 4, interests: ["music", "wellness"], scenes: ["ピアノの練習"], next: "電子楽器", budget: "3〜10万円",
      comment: "学生時代にやっていたピアノを再開したいです。マンションなのでヘッドホンで練習でき、場所をとらない電子ピアノが理想です。" } },
];

export function SurveyTab({ onSubmitted, onGoCustomer }: { onSubmitted: (pid?: string) => void; onGoCustomer: (pid: string) => void }) {
  const [kw, setKw] = useState("");
  const [list, setList] = useState<any[]>([]);
  const [who, setWho] = useState<any>(null);
  const [form, setForm] = useState<Form>(EMPTY);
  const [products, setProducts] = useState<any[]>([]);
  const [sent, setSent] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { get("/api/products").then(setProducts).catch(() => {}); }, []);
  useEffect(() => { const t = setTimeout(() => get(`/api/customers?q=${encodeURIComponent(kw)}`).then(setList).catch((e) => setErr(e.message)), 250); return () => clearTimeout(t); }, [kw]);
  const pick = async (c: any) => {
    const d = await get(`/api/customers/${encodeURIComponent(c.profile_id)}`);
    setWho({ ...c, respondent: d.respondent, owned: d.customer.owned_products });
  };
  const toggle = (k: "interests" | "scenes" | "owned", v: string) =>
    setForm((f) => ({ ...f, [k]: f[k].includes(v) ? f[k].filter((x) => x !== v) : [...f[k], v] }));
  const survey = SURVEYS.find((s) => s.id === form.surveyId)!;
  const r = who?.respondent;
  const body = {
    surveyId: survey.id, surveyName: survey.name, contactId: r?.contact_id, customerName: who?.display_name, nps: form.nps, satisfaction: form.satisfaction, interests: form.interests,
    scenes: form.scenes, next: form.next, budget: form.budget, owned: form.owned, comment: form.comment,
    contact: r ? { fullName: r.full_name, email: r.email, phone: r.phone, postalCode: r.postal_code, prefecture: r.prefecture, ageBand: r.age_band, gender: r.gender } : undefined,
  };
  const submit = async () => {
    setBusy(true); setErr("");
    try { const res = await post("/api/survey/submit", body); setSent(res); onSubmitted(res.profileId); }
    catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="grid-survey">
      <aside className="card">
        <h3>回答する顧客を選ぶ</h3>
        <p className="muted small">Qualtrics の連絡先リストにいる顧客（名寄せ済み）</p>
        <input className="search" placeholder="氏名・メールで検索" value={kw} onChange={(e) => setKw(e.target.value)} />
        <ul className="pick-list">
          {list.map((c) => (
            <li key={c.profile_id} className={who?.profile_id === c.profile_id ? "on" : ""} onClick={() => pick(c)}>
              <b>{c.display_name}</b><span className="muted small">{c.age_band}・{c.prefecture}</span>
              <span className="seg">{c.segment}</span>
            </li>
          ))}
        </ul>
      </aside>
      <section className="card qx">
        <div className="qx-head">
          <span className="qx-logo">XM</span>
          <div><b>{survey.name}</b><div className="muted small">Qualtrics（想定）で配信したアンケートの回答画面</div></div>
          <select value={form.surveyId} onChange={(e) => setForm({ ...form, surveyId: e.target.value })}>
            {SURVEYS.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <div className="presets">回答例：{PRESETS.map((p) => <button key={p.label} onClick={() => setForm({ ...EMPTY, ...p.f })}>{p.label}</button>)}</div>
        {who ? <div className="who">回答者：<b>{who.display_name}</b>（{r?.contact_id}・{r?.email}） <span className="seg">現在：{who.segment}</span></div>
             : <div className="who warn">左のリストから回答する顧客を選んでください</div>}
        <div className="q"><label>Q1. 友人や家族に CASIO 製品をすすめる可能性は？（0〜10）</label>
          <div className="nps">{Array.from({ length: 11 }, (_, i) => <button key={i} className={form.nps === i ? "on" : ""} onClick={() => setForm({ ...form, nps: i })}>{i}</button>)}</div></div>
        <div className="q"><label>Q2. お持ちの製品の満足度</label>
          <div className="stars">{[1, 2, 3, 4, 5].map((i) => <button key={i} className={form.satisfaction >= i ? "on" : ""} onClick={() => setForm({ ...form, satisfaction: i })}>★</button>)}</div></div>
        <div className="q"><label>Q3. 関心のあること（複数可）</label>
          <div className="chips">{DIMS.map((d) => <button key={d} className={form.interests.includes(d) ? "on" : ""} onClick={() => toggle("interests", d)}>{DIM_LABEL[d]}</button>)}</div></div>
        <div className="q"><label>Q4. 使いたい場面（複数可）</label>
          <div className="chips">{SCENES.map((s) => <button key={s} className={form.scenes.includes(s) ? "on" : ""} onClick={() => toggle("scenes", s)}>{s}</button>)}</div></div>
        <div className="q row2">
          <div><label>Q5. 次に欲しい製品</label><select value={form.next} onChange={(e) => setForm({ ...form, next: e.target.value })}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select></div>
          <div><label>Q6. ご予算</label><div className="chips">{BUDGETS.map((b) => <button key={b} className={form.budget === b ? "on" : ""} onClick={() => setForm({ ...form, budget: b })}>{b}</button>)}</div></div>
        </div>
        <div className="q"><label>Q7. お持ちの製品（任意）</label>
          <select value="" onChange={(e) => e.target.value && toggle("owned", e.target.value)}>
            <option value="">製品を追加…</option>{products.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_name}</option>)}
          </select>
          <div className="chips">{form.owned.map((o) => <button key={o} className="on" onClick={() => toggle("owned", o)}>{products.find((p) => p.product_id === o)?.product_name ?? o} ✕</button>)}</div></div>
        <div className="q"><label>Q8. ご意見・ご要望（自由記述 → AI が分類）</label>
          <textarea rows={3} value={form.comment} onChange={(e) => setForm({ ...form, comment: e.target.value })} placeholder="製品の感想や、これから欲しいものを自由にお書きください" /></div>
        <div className="actions">
          <button className="primary" disabled={!who || busy || !form.interests.length} onClick={submit}>{busy ? "送信中…" : "回答を送信する"}</button>
          {sent?.profileId && <button onClick={() => onGoCustomer(sent.profileId)}>この顧客のレコメンドを見る →</button>}
          {err && <span className="err">{err}</span>}
        </div>
      </section>
      <aside className="card payload">
        <h3>Webhook で届くデータ</h3>
        <p className="muted small">Qualtrics のワークフロー（Web サービス）から、この形式で <code>/api/qualtrics/webhook</code> に届く想定</p>
        <pre>{JSON.stringify(sent?.payload ?? { responseId: "R_…", surveyId: survey.id, contactId: r?.contact_id ?? "CNT_…", recordedDate: "…",
          values: { QID1_NPS: form.nps, QID2_SAT: form.satisfaction, QID3_OWNED: form.owned, QID4_INTEREST: form.interests, QID5_NEXT: form.next, QID6_BUDGET: form.budget, QID7_SCENE: form.scenes, QID8_TEXT: form.comment } }, null, 2)}</pre>
      </aside>
    </div>
  );
}
