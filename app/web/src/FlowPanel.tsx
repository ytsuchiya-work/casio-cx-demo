import { useEffect, useState } from "react";

export interface Ev { flowId: string; step: string; status: "running" | "done" | "error" | "skipped"; at: number; startAt?: number; detail?: string; data?: any; }
export interface FlowState { flowId: string; contactId?: string; customerName?: string; startedAt: number; events: Ev[]; }

// 画面上部に並べる処理の段（ジョブのタスクは CDF 到着後に順に動く）
export const NODES: { id: string; steps: string[]; title: string; sub: string; tech: string; color: string }[] = [
  { id: "qualtrics", steps: ["qualtrics"], title: "アンケート回答", sub: "Qualtrics（想定）", tech: "Webhook で受信", color: "#6B4FBB" },
  { id: "lakebase", steps: ["lakebase"], title: "回答を保存", sub: "Lakebase", tech: "Postgres に INSERT", color: "#1B5161" },
  { id: "cdf", steps: ["cdf"], title: "Lakehouse へ連携", sub: "Lakebase CDF", tech: "Delta 履歴テーブル", color: "#1B5161" },
  { id: "queue", steps: ["queue", "prepare"], title: "ジョブ起動・準備", sub: "Lakeflow Jobs", tech: "サーバーレス", color: "#FF3621" },
  { id: "classify", steps: ["classify"], title: "AI で分類", sub: "モデルサービス", tech: "話題・感情・関心", color: "#FF3621" },
  { id: "build_gold", steps: ["build_gold"], title: "顧客360・集計", sub: "Profile Agents", tech: "CustomerLake 名寄せ", color: "#00A972" },
  { id: "campaign_reco", steps: ["campaign_reco"], title: "キャンペーン・推薦", sub: "Campaign Agents", tech: "CustomerLake 対象者", color: "#00A972" },
  { id: "sync_lakebase", steps: ["sync_lakebase"], title: "Lakebase へ配信", sub: "同期テーブル", tech: "LTAP Direct Writes", color: "#1B5161" },
  { id: "app", steps: ["app"], title: "レコメンド表示", sub: "React アプリ", tech: "顧客ごとに更新", color: "#6B4FBB" },
];
const STEP_LABEL: Record<string, string> = { qualtrics: "Qualtrics 受信", lakebase: "Lakebase 書き込み", cdf: "CDF → Delta", queue: "ジョブ起動待ち",
  prepare: "準備（最新化）", classify: "AI 分類", build_gold: "顧客360・集計", campaign_reco: "キャンペーン・推薦", sync_lakebase: "同期テーブル更新", app: "アプリ反映" };
const ORDER = ["qualtrics", "lakebase", "cdf", "queue", "prepare", "classify", "build_gold", "campaign_reco", "sync_lakebase", "app"];

function stepState(f: FlowState | undefined, step: string) {
  const evs = (f?.events ?? []).filter((e) => e.step === step);
  if (!evs.length) return null;
  const last = evs[evs.length - 1];
  const first = evs[0];
  const start = last.startAt ?? first.startAt ?? first.at;
  return { status: last.status, start, end: last.status === "running" ? undefined : last.at, detail: [...evs].reverse().find((e) => e.detail)?.detail };
}
const fmt = (ms: number) => (ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} 秒`);

export function FlowPanel({ flow, flows, onSelect }: { flow?: FlowState; flows: FlowState[]; onSelect: (id: string) => void }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(t); }, []);
  const t0 = flow?.startedAt ?? now;
  const appDone = stepState(flow, "app");
  const tEnd = appDone?.end ?? now;
  const raw = Math.max(10_000, tEnd - t0 + 3000);
  const step = [5, 10, 15, 30, 60, 120].find((s) => raw / 1000 / s <= 8) ?? 300;
  const total = Math.ceil(raw / 1000 / step) * step * 1000;
  const ticks = Array.from({ length: total / 1000 / step + 1 }, (_, i) => i * step * 1000);
  return (
    <section className="flow">
      <div className="flow-head">
        <div>
          <h2>データの流れ（リアルタイム）</h2>
          <p className="muted">アンケート1件が、保存 → Lakehouse 連携 → AI 分類・集計 → Lakebase 配信 → レコメンドへと流れる様子</p>
        </div>
        <div className="flow-pick">
          {flow ? <span className="badge">{flow.customerName ?? flow.contactId}・{flow.flowId}</span> : <span className="muted">まだ回答がありません</span>}
          {flows.length > 1 && (
            <select value={flow?.flowId} onChange={(e) => onSelect(e.target.value)}>
              {flows.map((f) => <option key={f.flowId} value={f.flowId}>{new Date(f.startedAt).toLocaleTimeString("ja-JP")} {f.customerName ?? f.contactId}</option>)}
            </select>
          )}
          <span className="total">経過 {flow ? fmt(tEnd - t0) : "—"}</span>
        </div>
      </div>
      <div className="nodes">
        {NODES.map((n, i) => {
          const sts = n.steps.map((s) => stepState(flow, s)).filter(Boolean) as NonNullable<ReturnType<typeof stepState>>[];
          const status = !sts.length ? "idle" : sts.some((s) => s.status === "error") ? "error"
            : sts.length === n.steps.length && sts.every((s) => s.status === "done") ? "done" : "running";
          const start = sts.length ? Math.min(...sts.map((s) => s.start)) : 0;
          const end = status === "done" ? Math.max(...sts.map((s) => s.end ?? now)) : now;
          return (
            <div key={n.id} className="node-wrap">
              <div className={`node ${status}`} style={{ ["--c" as any]: n.color }}>
                <div className="node-no">{i + 1}</div>
                <div className="node-title">{n.title}</div>
                <div className="node-sub">{n.sub}</div>
                <div className="node-tech">{n.tech}</div>
                <div className="node-time">{status === "idle" ? "待機" : status === "error" ? "エラー" : fmt(Math.max(0, end - start))}</div>
              </div>
              {i < NODES.length - 1 && <div className={`arrow ${status === "done" ? "lit" : ""}`}>▶</div>}
            </div>
          );
        })}
      </div>
      <div className="timeline">
        <div className="tl-axis">
          {ticks.map((t) => <span key={t} style={{ left: `${(t / total) * 100}%` }}>{(t / 1000).toFixed(0)}s</span>)}
        </div>
        {ORDER.map((s) => {
          const st = stepState(flow, s);
          const left = st ? ((st.start - t0) / total) * 100 : 0;
          const width = st ? Math.max(0.6, (((st.end ?? now) - st.start) / total) * 100) : 0;
          return (
            <div key={s} className="tl-row">
              <div className="tl-label">{STEP_LABEL[s]}</div>
              <div className="tl-track">
                {st && <div className={`tl-bar ${st.status}`} style={{ left: `${Math.max(0, left)}%`, width: `${width}%` }} title={st.detail} />}
                {st && (Math.max(0, left) + width > 62
                  ? <span className="tl-text" style={{ right: `calc(${100 - Math.max(0, left)}% + 6px)` }}>{fmt((st.end ?? now) - st.start)}{st.detail ? `｜${st.detail}` : ""}</span>
                  : <span className="tl-text" style={{ left: `${Math.max(0, left) + width + 0.5}%` }}>{fmt((st.end ?? now) - st.start)}{st.detail ? `｜${st.detail}` : ""}</span>)}
              </div>
            </div>
          );
        })}
        {flow && !appDone && <div className="tl-now" style={{ left: `calc(170px + (100% - 170px) * ${(now - t0) / total})` }} />}
      </div>
    </section>
  );
}
