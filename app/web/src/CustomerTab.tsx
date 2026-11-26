import { useEffect, useState } from "react";
import { get, DIMS, DIM_LABEL, yen, parseArr } from "./api";

export function CustomerTab({ profileId, onSelect, flowResult, flowRunning }: { profileId?: string; onSelect: (id: string) => void; flowResult?: any; flowRunning: boolean }) {
  const [kw, setKw] = useState("");
  const [list, setList] = useState<any[]>([]);
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => { const t = setTimeout(() => get(`/api/customers?q=${encodeURIComponent(kw)}`).then(setList).catch((e) => setErr(e.message)), 250); return () => clearTimeout(t); }, [kw]);
  const load = (id: string) => get(`/api/customers/${encodeURIComponent(id)}`).then(setD).catch((e) => setErr(e.message));
  useEffect(() => { if (profileId) load(profileId); }, [profileId]);
  // フローが終わったら最新を読み直す
  useEffect(() => { if (flowResult?.profileId && flowResult.profileId === profileId) load(profileId!); }, [flowResult]);
  const c = d?.customer;
  const showDiff = flowResult && c && flowResult.profileId === c.profile_id;
  const beforeIds: string[] = showDiff ? (flowResult.before ?? []).map((x: any) => x.product_id) : [];

  return (
    <div className="grid-customer">
      <aside className="card">
        <h3>顧客を探す</h3>
        <input className="search" placeholder="氏名・メール・顧客IDで検索" value={kw} onChange={(e) => setKw(e.target.value)} />
        <ul className="pick-list">
          {list.map((x) => (
            <li key={x.profile_id} className={c?.profile_id === x.profile_id ? "on" : ""} onClick={() => onSelect(x.profile_id)}>
              <b>{x.display_name}</b><span className="muted small">{x.sources}</span><span className="seg">{x.segment}</span>
            </li>
          ))}
        </ul>
        {err && <p className="err">{err}</p>}
      </aside>
      {!c ? <section className="card empty">左のリストから顧客を選ぶと、名寄せ後のプロフィールとおすすめ製品が表示されます。</section> : (
        <>
          <section className="card profile">
            <div className="p-head">
              <div className="avatar">{c.display_name?.slice(0, 1)}</div>
              <div>
                <h3>{c.display_name}</h3>
                <div className="muted small">{c.age_band}・{c.gender}・{c.prefecture}　{c.email}</div>
              </div>
              <span className="seg big">{c.segment}</span>
            </div>
            <div className="ids">
              <div><span>名寄せ後の顧客 ID</span><code>{c.profile_id}</code></div>
              <div><span>CASIO ID</span><code>{c.member_id ?? "—"}</code></div>
              <div><span>オンラインストア</span><code>{c.customer_no ?? "—"}</code></div>
              <div><span>Qualtrics 連絡先</span><code>{(d.contactIds ?? []).join(", ") || "—"}</code></div>
            </div>
            <p className="muted small">CustomerLake Profile Agents が {c.source_count} つのシステムの記録を1人にまとめた顧客（{c.sources}）</p>
            <div className="kpis">
              <div><b>{c.last_nps ?? "—"}</b><span>直近の NPS（{c.nps_group ?? "—"}）</span></div>
              <div><b>{c.response_count}</b><span>回答数</span></div>
              <div><b>{c.order_count}</b><span>ストア注文</span></div>
              <div><b>{yen(c.total_spend ?? 0)}</b><span>購入金額</span></div>
            </div>
            <h4>関心スコア（アンケート＋AI 分類＋購入履歴）</h4>
            <div className="bars">
              {DIMS.map((k) => { const v = Number(c[`score_${k}`] ?? 0); return (
                <div key={k} className="bar-row"><span>{DIM_LABEL[k]}</span><div className="bar"><i style={{ width: `${v * 100}%` }} /></div><em>{v.toFixed(2)}</em></div>); })}
            </div>
            <h4>キャンペーン（CustomerLake Campaign Agents のオーディエンス）</h4>
            <div className="chips">{d.campaigns.length ? d.campaigns.map((x: any) => <span key={x.audience_id} className="camp">{x.audience_name}<small>{x.offer}</small></span>) : <span className="muted small">対象のキャンペーンなし</span>}</div>
            <h4>最近の回答</h4>
            <ul className="resp">
              {d.responses.map((r: any) => (
                <li key={r.response_id}><span className="muted small">{new Date(r.submitted_at).toLocaleString("ja-JP")}・{r.survey_name}・NPS {r.nps}</span><p>{r.comment}</p>
                  <div className="chips">{parseArr(r.interests).map((x) => <span key={x} className="tag">{DIM_LABEL[x] ?? x}</span>)}</div></li>
              ))}
            </ul>
          </section>
          <section className="card recos">
            <div className="r-head"><h3>おすすめ製品</h3>{flowRunning && profileId === c.profile_id && <span className="badge pulse">新しい回答を処理中…</span>}</div>
            <p className="muted small">Lakehouse で集計した結果を、同期テーブル（LTAP Direct Writes）で Lakebase に配信し、ここで読み出している</p>
            {showDiff && <div className="diff">回答を反映して更新しました（{new Date(c.updated_at).toLocaleTimeString("ja-JP")}）</div>}
            <ol>
              {d.recommendations.map((r: any) => {
                const isNew = showDiff && !beforeIds.includes(r.product_id);
                return (
                  <li key={r.product_id} className={isNew ? "new" : ""}>
                    <div className="rank">{r.rank}</div>
                    <div className="r-body">
                      <a href={r.url} target="_blank"><b>{r.product_name}</b></a>
                      <div className="muted small">{r.series}・{r.category}・{r.model}</div>
                      <div className="reason">{r.reason || "関心と購入傾向から"}</div>
                      {r.campaign && <div className="camp-line">🎁 {r.campaign}：{r.offer}</div>}
                    </div>
                    <div className="r-side"><b>{yen(r.price)}</b><div className="score"><i style={{ width: `${Math.min(100, r.score * 100)}%` }} /></div><small>スコア {Number(r.score).toFixed(2)}</small>{isNew && <span className="newtag">NEW</span>}</div>
                  </li>
                );
              })}
            </ol>
            {showDiff && (flowResult.before ?? []).length > 0 && (
              <div className="before"><h4>回答前のおすすめ</h4><ol>{flowResult.before.map((r: any) => <li key={r.product_id}>{r.product_name}</li>)}</ol></div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
