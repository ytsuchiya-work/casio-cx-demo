import { useEffect, useState } from "react";
import { get, yen } from "./api";

export function SummaryTab({ refreshKey }: { refreshKey?: number }) {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => { get("/api/summary").then(setD).catch((e) => setErr(e.message)); }, [refreshKey]);
  if (err) return <p className="err">{err}</p>;
  if (!d) return <p className="muted">読み込み中…</p>;
  const segs: string[] = d.segments.map((s: any) => s.segment);
  const topics: string[] = [...new Set<string>(d.topics.map((t: any) => t.topic))];
  const cell = (seg: string, topic: string) => d.topics.find((t: any) => t.segment === seg && t.topic === topic);
  const maxT = Math.max(...d.topics.map((t: any) => Number(t.total)), 1);
  const maxC = Math.max(...d.segments.map((s: any) => Number(s.customers)), 1);
  return (
    <div className="grid-summary">
      <section className="card">
        <h3>セグメント別の集計</h3>
        <p className="muted small">約1万件の回答を Lakehouse で AI 分類・集計し、Lakebase の同期テーブルから表示（更新 {d.segments[0] && new Date(d.segments[0].updated_at).toLocaleString("ja-JP")}）</p>
        <table className="tbl">
          <thead><tr><th>セグメント</th><th>顧客数</th><th>回答数</th><th>NPS</th><th>好意的な声</th><th>平均購入額</th></tr></thead>
          <tbody>{d.segments.map((s: any) => (
            <tr key={s.segment}><td><span className="seg">{s.segment}</span></td>
              <td><div className="hbar"><i style={{ width: `${(s.customers / maxC) * 100}%` }} /><span>{Number(s.customers).toLocaleString()}</span></div></td>
              <td>{Number(s.responses).toLocaleString()}</td><td className={s.nps_score >= 0 ? "pos" : "neg"}>{Number(s.nps_score).toFixed(1)}</td>
              <td>{Math.round(s.positive_ratio * 100)}%</td><td>{yen(s.avg_spend ?? 0)}</td></tr>))}</tbody>
        </table>
      </section>
      <section className="card">
        <h3>話題 × セグメント（AI 分類の結果）</h3>
        <p className="muted small">色の濃さ＝件数、バーの緑・灰・赤＝好意的・中立・否定的の割合</p>
        <div className="heat" style={{ gridTemplateColumns: `150px repeat(${segs.length}, 1fr)` }}>
          <div />{segs.map((s) => <div key={s} className="hh">{s}</div>)}
          {topics.map((t) => (
            <>
              <div key={t} className="hl">{t}</div>
              {segs.map((s) => { const c = cell(s, t); const n = Number(c?.total ?? 0); return (
                <div key={s + t} className="hc" style={{ background: `rgba(27,81,97,${0.06 + 0.7 * (n / maxT)})`, color: n / maxT > 0.5 ? "#fff" : "#1B3037" }} title={`${t} / ${s}`}>
                  <b>{n}</b>
                  {c && <div className="sent"><i className="p" style={{ flex: c.positive }} /><i className="u" style={{ flex: c.neutral }} /><i className="n" style={{ flex: c.negative }} /></div>}
                </div>); })}
            </>
          ))}
        </div>
      </section>
      <section className="card">
        <h3>キャンペーン（CustomerLake のオーディエンス）</h3>
        <table className="tbl"><thead><tr><th>オーディエンス</th><th>対象シリーズ</th><th>オファー</th><th>対象者</th></tr></thead>
          <tbody>{d.campaigns.map((c: any) => <tr key={c.audience_id}><td><b>{c.audience_name}</b></td><td>{c.series}</td><td>{c.offer}</td><td>{c.members.toLocaleString()} 人</td></tr>)}</tbody></table>
      </section>
    </div>
  );
}

export function CustomerLakeTab() {
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => { get("/api/customerlake").then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <p className="err">{err}</p>;
  if (!d) return <p className="muted">読み込み中…（Databricks SQL で集計しています）</p>;
  const s = d.sources;
  const rec = Number(s.members) + Number(s.store) + Number(s.survey);
  return (
    <div className="grid-cl">
      <section className="card">
        <h3>Profile Agents：3 つのシステムの記録を1人の顧客に</h3>
        <p className="muted small">共通の顧客 ID がない記録を、氏名・メール・電話・住所の表記ゆれを吸収して名寄せ（ルールは Genie が提案）</p>
        <div className="idr">
          <div className="srcs">
            <div className="src"><b>{Number(s.members).toLocaleString()}</b><span>CASIO ID 会員</span></div>
            <div className="src"><b>{Number(s.store).toLocaleString()}</b><span>オンラインストア顧客</span></div>
            <div className="src"><b>{Number(s.survey).toLocaleString()}</b><span>Qualtrics 回答者</span></div>
          </div>
          <div className="idr-arrow">合計 {rec.toLocaleString()} 件 ▶ 名寄せ</div>
          <div className="src gold"><b>{Number(s.profiles).toLocaleString()}</b><span>顧客プロファイル</span><small>2 システム以上 {Number(s.multi).toLocaleString()} 人／3 システム {Number(s.three).toLocaleString()} 人</small></div>
        </div>
      </section>
      <section className="card">
        <h3>Campaign Agents：Genie で作ったオーディエンス</h3>
        <p className="muted small">顧客 360 テーブル（gold_customer_360）をエンティティにし、自然文で条件を書いて作成。結果は Unity Catalog のビューになる</p>
        <table className="tbl"><thead><tr><th>オーディエンス</th><th>シリーズ</th><th>オファー</th><th>対象者</th></tr></thead>
          <tbody>{d.audiences.map((a: any) => <tr key={a.audience_id}><td><b>{a.audience_name}</b><div className="muted small"><code>audiences.{a.audience_id}</code></div></td><td>{a.series}</td><td>{a.offer}</td><td>{Number(a.members).toLocaleString()} 人</td></tr>)}</tbody></table>
        <a className="btn" href={d.links.customerlake} target="_blank">CustomerLake を開く</a>
      </section>
    </div>
  );
}
