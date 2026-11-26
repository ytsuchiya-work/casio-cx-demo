export async function get<T = any>(path: string): Promise<T> {
  const r = await fetch(path); const j = await r.json();
  if (!r.ok) throw new Error(j.error ?? r.statusText); return j as T;
}
export async function post<T = any>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json(); if (!r.ok) throw new Error(j.error ?? r.statusText); return j as T;
}
export const DIMS = ["outdoor", "sports", "business", "luxury", "fashion", "music", "study", "office", "tech", "wellness", "family"] as const;
export const DIM_LABEL: Record<string, string> = { outdoor: "アウトドア", sports: "スポーツ", business: "ビジネス", luxury: "上質・高級", fashion: "ファッション",
  music: "音楽", study: "学び", office: "事務・実務", tech: "スマート連携", wellness: "癒やし", family: "家族・ギフト" };
export const SCENES = ["登山", "キャンプ", "釣り", "トレイルラン", "ランニング", "ジム", "サーフィン", "通勤", "商談", "出張", "フォーマル", "記念日",
  "街歩き", "コーデのアクセント", "ピアノの練習", "弾き語り", "作曲", "受験勉強", "語学学習", "資格の勉強", "事務作業", "リラックスタイム", "家族へのプレゼント", "スマホ連携"];
export const SURVEYS = [
  { id: "SV_8dWatchSat2026", name: "腕時計 ご購入者満足度アンケート" },
  { id: "SV_3fLifeInterest", name: "ライフスタイルと製品への関心アンケート" },
  { id: "SV_6aLearnMusic26", name: "学び・音楽製品アンケート" },
];
export const CATEGORIES = ["腕時計", "電子辞書", "電卓", "電子楽器", "ラベルライター", "AIペット"];
export const BUDGETS = ["〜1万円", "1〜3万円", "3〜10万円", "10万円以上"];
export const yen = (n: number) => "¥" + Number(n).toLocaleString("ja-JP");
export const parseArr = (v: any): string[] => Array.isArray(v) ? v : typeof v === "string" ? (v.startsWith("[") ? JSON.parse(v) : v.replace(/[{}"]/g, "").split(",").filter(Boolean)) : [];
