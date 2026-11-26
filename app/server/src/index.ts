import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomBytes } from "node:crypto";
import { cfg, uc, workspaceUrl } from "./config.js";
import { q, lakebaseHost } from "./lakebase.js";
import { sql } from "./dbsql.js";
import { bus, flows, ingest, QualtricsPayload } from "./pipeline.js";

const app = express();
app.use(express.json({ limit: "1mb" }));
const S = cfg.serving;
const wrap = (fn: (req: express.Request, res: express.Response) => Promise<any>) =>
  (req: express.Request, res: express.Response) => fn(req, res).then((d) => d !== undefined && res.json(d)).catch((e) => {
    console.error(e); res.status(500).json({ error: String(e.message ?? e) });
  });

app.get("/api/health", wrap(async () => ({ ok: true, lakebase: (await q("select now() as now"))[0].now, host: lakebaseHost() })));

app.get("/api/config", wrap(async () => ({
  workspace: cfg.host, catalog: cfg.catalog, schema: cfg.schema, serving: S,
  links: {
    job: workspaceUrl(`/jobs/${cfg.jobId}`),
    lakebase: workspaceUrl(`/lakebase/projects/${cfg.lbEndpoint.split("/")[1]}`),
    customerlake: workspaceUrl(`/customerlake`),
    catalog: workspaceUrl(`/explore/data/${cfg.catalog}/${cfg.schema}`),
  },
})));

app.get("/api/products", wrap(async () => q(`SELECT product_id, product_name, model, series, category, price, url FROM ${S}.products ORDER BY product_id`)));

// 顧客検索（Lakebase の同期テーブル）
app.get("/api/customers", wrap(async (req) => {
  const kw = String(req.query.q ?? "").trim();
  const seg = String(req.query.segment ?? "").trim();
  const params: any[] = [];
  let where = "response_count > 0";
  if (kw) { params.push(`%${kw}%`); where += ` AND (display_name ILIKE $${params.length} OR email ILIKE $${params.length} OR profile_id ILIKE $${params.length})`; }
  if (seg) { params.push(seg); where += ` AND segment = $${params.length}`; }
  return q(`SELECT profile_id, display_name, email, prefecture, age_band, segment, sources, source_count, response_count, last_nps, contact_id
            FROM ${S}.customers WHERE ${where} ORDER BY source_count DESC, last_response_at DESC NULLS LAST LIMIT 40`, params);
}));

app.get("/api/customers/:id", wrap(async (req) => {
  const id = req.params.id;
  const [c] = await q(`SELECT * FROM ${S}.customers WHERE profile_id = $1`, [id]);
  if (!c) return { notFound: true };
  const [recos, camps, contacts] = await Promise.all([
    q(`SELECT * FROM ${S}.recommendations WHERE profile_id = $1 ORDER BY rank`, [id]),
    q(`SELECT audience_id, audience_name, series, offer FROM ${S}.campaign_members WHERE profile_id = $1`, [id]),
    q(`SELECT contact_id FROM ${S}.contact_profile WHERE profile_id = $1`, [id]),
  ]);
  const ids = contacts.map((x: any) => x.contact_id);
  const responses = ids.length ? await q(`SELECT response_id, survey_name, submitted_at, nps, satisfaction, interests, usage_scenes, comment, next_purchase_category, budget_band
            FROM survey.responses WHERE contact_id = ANY($1) ORDER BY submitted_at DESC LIMIT 8`, [ids]) : [];
  const [resp] = ids.length ? await q(`SELECT contact_id, full_name, email, phone, postal_code, prefecture, age_band, gender FROM survey.respondents WHERE contact_id = ANY($1) ORDER BY updated_at DESC LIMIT 1`, [ids]) : [];
  return { customer: c, recommendations: recos, campaigns: camps, responses, respondent: resp ?? null, contactIds: ids };
}));

// 集計（Lakehouse で作った集計テーブルを Lakebase で配信）
app.get("/api/summary", wrap(async () => {
  const [segments, topics, campaigns] = await Promise.all([
    q(`SELECT * FROM ${S}.segment_summary ORDER BY customers DESC`),
    q(`SELECT segment, topic, positive, neutral, negative, total FROM ${S}.topic_summary ORDER BY total DESC`),
    q(`SELECT audience_id, audience_name, series, offer, count(*)::int AS members FROM ${S}.campaign_members GROUP BY 1,2,3,4 ORDER BY members DESC`),
  ]);
  return { segments, topics, campaigns };
}));

// CustomerLake（UC 上の名寄せ結果とオーディエンス）
let clCache: { at: number; data: any } | null = null;
app.get("/api/customerlake", wrap(async () => {
  if (clCache && Date.now() - clCache.at < 60_000) return clCache.data;
  const [src] = await sql(`SELECT (SELECT count(*) FROM ${uc("src_casio_id_members")}) AS members, (SELECT count(*) FROM ${uc("src_online_store_customers")}) AS store,
     (SELECT count(*) FROM ${uc("src_survey_respondents")}) AS survey, (SELECT count(*) FROM ${uc("gold_customer_360")}) AS profiles,
     (SELECT count(*) FROM ${uc("gold_customer_360")} WHERE source_count >= 2) AS multi, (SELECT count(*) FROM ${uc("gold_customer_360")} WHERE source_count = 3) AS three`);
  const auds = await sql(`SELECT a.audience_id, a.audience_name, a.series, a.offer, count(m.profile_id) AS members
     FROM ${uc("campaign_audiences")} a LEFT JOIN ${uc("gold_campaign_members")} m USING (audience_id) WHERE a.active GROUP BY ALL ORDER BY members DESC`);
  const data = { sources: src, audiences: auds, links: { customerlake: workspaceUrl("/customerlake") } };
  clCache = { at: Date.now(), data };
  return data;
}));

// Qualtrics の Webhook（ワークフローの「Web サービス」タスク）からの受信口
app.post("/api/qualtrics/webhook", wrap(async (req) => {
  const p = req.body as QualtricsPayload;
  if (!p?.responseId || !p?.contactId || !p?.values) throw new Error("responseId / contactId / values が必要");
  const f = await ingest(p);
  return { accepted: true, flowId: f.flowId, profileId: f.profileId };
}));

// アプリ内のアンケート画面から送信（Qualtrics の形式に変換して同じ受信口へ）
app.post("/api/survey/submit", wrap(async (req) => {
  const b = req.body;
  const payload: QualtricsPayload = {
    responseId: "R_" + randomBytes(11).toString("base64url").replace(/[-_]/g, "x").slice(0, 15),
    surveyId: b.surveyId, surveyName: b.surveyName, contactId: b.contactId || "CNT_" + randomBytes(8).toString("hex").slice(0, 10),
    recordedDate: new Date().toISOString(), distributionChannel: "web",
    values: { QID1_NPS: b.nps, QID2_SAT: b.satisfaction, QID3_OWNED: b.owned ?? [], QID4_INTEREST: b.interests ?? [], QID5_NEXT: b.next,
              QID6_BUDGET: b.budget, QID7_SCENE: b.scenes ?? [], QID8_TEXT: b.comment ?? "" },
    contact: b.contact,
  };
  const f = await ingest(payload, b.customerName);
  return { accepted: true, flowId: f.flowId, profileId: f.profileId, payload };
}));

app.get("/api/flows", wrap(async () => flows));

// SSE：データの流れをリアルタイムに配信
app.get("/api/events", (req, res) => {
  res.writeHead(200, { "Content-Type": "text/event-stream; charset=utf-8", "Cache-Control": "no-cache", Connection: "keep-alive", "X-Accel-Buffering": "no" });
  res.write(`event: hello\ndata: ${JSON.stringify({ flows })}\n\n`);
  const onEv = (e: any) => res.write(`event: step\ndata: ${JSON.stringify(e)}\n\n`);
  const onFlow = (e: any) => res.write(`event: flow\ndata: ${JSON.stringify(e)}\n\n`);
  bus.on("event", onEv); bus.on("flow", onFlow);
  const ping = setInterval(() => res.write(`: ping\n\n`), 15_000);
  req.on("close", () => { clearInterval(ping); bus.off("event", onEv); bus.off("flow", onFlow); });
});

const here = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(here, "../../web/dist");
app.use(express.static(web));
app.get(/^(?!\/api).*/, (_req, res) => res.sendFile(path.join(web, "index.html")));
app.listen(cfg.port, () => console.log(`CASIO CX demo: http://localhost:${cfg.port}`));
