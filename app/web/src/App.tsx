import { useEffect, useMemo, useState } from "react";
import { FlowPanel, FlowState, Ev } from "./FlowPanel";
import { SurveyTab } from "./SurveyTab";
import { CustomerTab } from "./CustomerTab";
import { SummaryTab, CustomerLakeTab } from "./InsightTabs";
import { get } from "./api";

const TABS = [
  { id: "survey", label: "① アンケート回答（Qualtrics）" },
  { id: "customer", label: "② 顧客ごとのレコメンド" },
  { id: "summary", label: "③ 集計（Lakehouse → Lakebase）" },
  { id: "cl", label: "④ CustomerLake" },
] as const;

export default function App() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("survey");
  const [flows, setFlows] = useState<FlowState[]>([]);
  const [sel, setSel] = useState<string>();
  const [profileId, setProfileId] = useState<string>();
  const [links, setLinks] = useState<any>({});
  const [conn, setConn] = useState(false);

  useEffect(() => { get("/api/config").then((c) => setLinks(c.links)).catch(() => {}); }, []);
  useEffect(() => {
    const es = new EventSource("/api/events");
    es.addEventListener("hello", (m: MessageEvent) => {
      setConn(true);
      const d = JSON.parse(m.data);
      setFlows(d.flows.map((f: any) => ({ flowId: f.flowId, contactId: f.contactId, customerName: f.customerName, startedAt: f.startedAt, events: f.events })));
    });
    es.addEventListener("flow", (m: MessageEvent) => {
      const f = JSON.parse(m.data);
      setFlows((fs) => [{ ...f, events: [] }, ...fs.filter((x) => x.flowId !== f.flowId)].slice(0, 20));
      setSel(f.flowId);
    });
    es.addEventListener("step", (m: MessageEvent) => {
      const e: Ev = JSON.parse(m.data);
      setFlows((fs) => fs.map((f) => (f.flowId === e.flowId ? { ...f, events: [...f.events, e] } : f)));
    });
    es.onerror = () => setConn(false);
    return () => es.close();
  }, []);
  const flow = useMemo(() => flows.find((f) => f.flowId === sel) ?? flows[0], [flows, sel]);
  const appEv = flow?.events.find((e) => e.step === "app" && e.status === "done");

  return (
    <div className="page">
      <header className="top">
        <div className="brand">
          <span className="logo">CASIO</span>
          <div>
            <h1>カスタマーインサイト・デモ</h1>
            <p>Qualtrics のアンケート × Lakebase × Lakehouse × CustomerLake で、顧客ごとのおすすめを届ける</p>
          </div>
        </div>
        <div className="top-right">
          <span className={`dot ${conn ? "on" : ""}`} />{conn ? "リアルタイム接続中" : "接続待ち"}
          {links.job && <a href={links.job} target="_blank">ジョブ</a>}
          {links.lakebase && <a href={links.lakebase} target="_blank">Lakebase</a>}
          {links.customerlake && <a href={links.customerlake} target="_blank">CustomerLake</a>}
        </div>
      </header>
      <FlowPanel flow={flow} flows={flows} onSelect={setSel} />
      <nav className="tabs">
        {TABS.map((t) => <button key={t.id} className={tab === t.id ? "on" : ""} onClick={() => setTab(t.id)}>{t.label}</button>)}
      </nav>
      <main>
        {tab === "survey" && <SurveyTab onSubmitted={(pid) => { if (pid) setProfileId(pid); }} onGoCustomer={(pid) => { setProfileId(pid); setTab("customer"); }} />}
        {tab === "customer" && <CustomerTab profileId={profileId} onSelect={setProfileId} flowResult={appEv?.data} flowRunning={!!flow && !appEv} />}
        {tab === "summary" && <SummaryTab refreshKey={appEv?.at} />}
        {tab === "cl" && <CustomerLakeTab />}
      </main>
      <footer>デモ用の架空データです。製品名・型番・価格は casio.com/jp の掲載内容（2026年11月25日時点）を参考にしています。</footer>
    </div>
  );
}
