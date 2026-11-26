// 1件の回答が「Qualtrics → Lakebase → CDF → Lakehouse（AI 分類・集計・CustomerLake）→ 同期テーブル → アプリ」を
// 通り抜ける様子を追跡し、SSE で画面に流す
import { EventEmitter } from "node:events";
import { cfg, uc } from "./config.js";
import { api } from "./auth.js";
import { q } from "./lakebase.js";
import { sql } from "./dbsql.js";

export type StepId = "qualtrics" | "lakebase" | "cdf" | "queue" | "prepare" | "classify" | "build_gold" | "campaign_reco" | "sync_lakebase" | "app";
export interface FlowEvent { flowId: string; step: StepId; status: "running" | "done" | "error" | "skipped"; at: number; startAt?: number; detail?: string; data?: any; }
export interface Flow { flowId: string; contactId: string; profileId?: string; customerName?: string; startedAt: number; events: FlowEvent[]; runId?: number; finishedAt?: number; before?: any[]; after?: any[]; }

export const bus = new EventEmitter();
bus.setMaxListeners(100);
export const flows: Flow[] = [];
const JOB_TASKS: StepId[] = ["prepare", "classify", "build_gold", "campaign_reco", "sync_lakebase"];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function emit(f: Flow, e: Omit<FlowEvent, "flowId">) {
  const ev = { flowId: f.flowId, ...e };
  f.events.push(ev);
  bus.emit("event", ev);
}

export interface QualtricsPayload {
  responseId: string; surveyId: string; surveyName: string; contactId: string; recordedDate: string;
  values: { QID1_NPS: number; QID2_SAT: number; QID3_OWNED: string[]; QID4_INTEREST: string[]; QID5_NEXT: string; QID6_BUDGET: string; QID7_SCENE: string[]; QID8_TEXT: string };
  contact?: { fullName: string; email?: string; phone?: string; postalCode?: string; prefecture?: string; ageBand?: string; gender?: string };
  distributionChannel?: string;
}

export async function profileOf(contactId: string): Promise<string | undefined> {
  const r = await q(`SELECT profile_id FROM ${cfg.serving}.contact_profile WHERE contact_id = $1`, [contactId]).catch(() => []);
  return r[0]?.profile_id;
}
export async function recosOf(profileId: string) {
  return q(`SELECT rank, product_id, product_name, series, category, price, score, reason, campaign, offer, url, updated_at
            FROM ${cfg.serving}.recommendations WHERE profile_id = $1 ORDER BY rank`, [profileId]);
}

export async function ingest(p: QualtricsPayload, displayName?: string): Promise<Flow> {
  const t0 = Date.now();
  const f: Flow = { flowId: p.responseId, contactId: p.contactId, startedAt: t0, events: [], customerName: displayName ?? p.contact?.fullName };
  flows.unshift(f); flows.splice(20);
  bus.emit("flow", { flowId: f.flowId, contactId: f.contactId, startedAt: t0, customerName: f.customerName });
  emit(f, { step: "qualtrics", status: "done", at: t0, startAt: t0, detail: `${p.surveyName}（${p.responseId}）を受信` });

  // ② Lakebase へ書き込み（OLTP）
  const t1 = Date.now();
  emit(f, { step: "lakebase", status: "running", at: t1 });
  const v = p.values;
  if (p.contact) {
    await q(`INSERT INTO survey.respondents (contact_id, full_name, email, phone, postal_code, prefecture, age_band, gender)
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
             ON CONFLICT (contact_id) DO UPDATE SET full_name = EXCLUDED.full_name, email = EXCLUDED.email, phone = EXCLUDED.phone,
               postal_code = EXCLUDED.postal_code, prefecture = EXCLUDED.prefecture, age_band = EXCLUDED.age_band, gender = EXCLUDED.gender, updated_at = now()`,
      [p.contactId, p.contact.fullName, p.contact.email ?? null, p.contact.phone ?? "", p.contact.postalCode ?? "", p.contact.prefecture ?? null, p.contact.ageBand ?? null, p.contact.gender ?? null]);
  }
  const ins = await q(`INSERT INTO survey.responses (response_id, survey_id, survey_name, contact_id, submitted_at, nps, satisfaction, owned_products, interests,
             next_purchase_category, budget_band, usage_scenes, comment, channel, raw_payload)
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15) RETURNING clock_timestamp() AS committed_at`,
    [p.responseId, p.surveyId, p.surveyName, p.contactId, p.recordedDate, v.QID1_NPS, v.QID2_SAT, v.QID3_OWNED, v.QID4_INTEREST, v.QID5_NEXT,
     v.QID6_BUDGET, v.QID7_SCENE, v.QID8_TEXT, p.distributionChannel ?? "web", JSON.stringify(p)]);
  const committed = new Date(ins[0].committed_at).getTime();
  emit(f, { step: "lakebase", status: "done", at: Date.now(), startAt: t1, detail: `survey.responses に INSERT（${Date.now() - t1} ms）` });

  f.profileId = await profileOf(p.contactId);
  if (f.profileId) f.before = await recosOf(f.profileId).catch(() => []);
  track(f, committed).catch((e) => emit(f, { step: "app", status: "error", at: Date.now(), detail: String(e.message ?? e) }));
  return f;
}

async function track(f: Flow, committed: number) {
  // ③ Lakebase CDF → Lakehouse（Delta の履歴テーブル）に届くまで待つ
  const t2 = Date.now();
  emit(f, { step: "cdf", status: "running", at: t2, startAt: committed });
  let arrived = 0;
  for (let i = 0; i < 300 && !arrived; i++) {
    const r = await sql(`SELECT max(_timestamp) AS ts FROM ${uc("lb_responses_history")} WHERE response_id = :id`, [{ name: "id", value: f.flowId }]);
    if (r[0]?.ts) arrived = Date.now();
    else await sleep(1500);
  }
  if (!arrived) { emit(f, { step: "cdf", status: "error", at: Date.now(), detail: "5分以内に届かなかった" }); return; }
  emit(f, { step: "cdf", status: "done", at: arrived, startAt: committed, detail: `lb_responses_history に到着（書き込みから ${((arrived - committed) / 1000).toFixed(1)} 秒）` });

  // ④ Lakeflow ジョブ（分類・集計・CustomerLake・同期）を起動して各タスクを追う
  const run = await api<any>("POST", "/api/2.1/jobs/run-now", { job_id: cfg.jobId });
  f.runId = run.run_id;
  const tq = Date.now();
  emit(f, { step: "queue", status: "running", at: tq, startAt: tq, detail: `ジョブ実行 #${run.run_id} を開始（サーバーレス）`, data: { runId: run.run_id } });
  const seen = new Map<string, string>();
  let queueDone = false;
  for (;;) {
    const r = await api<any>("GET", `/api/2.1/jobs/runs/get?run_id=${run.run_id}`);
    for (const t of r.tasks ?? []) {
      const key = t.task_key as StepId;
      const lc = t.state?.life_cycle_state;
      const st = lc === "TERMINATED" || lc === "SKIPPED" || lc === "INTERNAL_ERROR" ? (t.state?.result_state === "SUCCESS" ? "done" : "error") : lc === "RUNNING" ? "running" : "";
      if (!st || seen.get(key) === st) continue;
      if (!queueDone && t.start_time) { queueDone = true; emit(f, { step: "queue", status: "done", at: Math.max(tq, t.start_time), startAt: tq, detail: "サーバーレスのジョブを起動" }); }
      seen.set(key, st);
      emit(f, { step: key, status: st as any, at: st === "running" ? (t.start_time || Date.now()) : (t.end_time || Date.now()), startAt: t.start_time || undefined,
                detail: st === "error" ? t.state?.state_message : undefined });
    }
    if (r.state?.life_cycle_state === "TERMINATED" || r.state?.life_cycle_state === "INTERNAL_ERROR") {
      if (r.state?.result_state !== "SUCCESS") { emit(f, { step: "app", status: "error", at: Date.now(), detail: "ジョブが失敗" }); return; }
      break;
    }
    await sleep(2000);
  }

  // ⑤ アプリ：Lakebase に反映された新しいレコメンドを読む
  const t5 = Date.now();
  f.profileId = (await profileOf(f.contactId)) ?? f.profileId;
  f.after = f.profileId ? await recosOf(f.profileId) : [];
  f.finishedAt = Date.now();
  emit(f, { step: "app", status: "done", at: f.finishedAt, startAt: t5, detail: `レコメンドを更新（全体 ${((f.finishedAt - f.startedAt) / 1000).toFixed(0)} 秒）`,
            data: { profileId: f.profileId, before: f.before ?? [], after: f.after } });
}
