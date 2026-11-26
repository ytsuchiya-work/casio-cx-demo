// Databricks への認証。SP（OAuth M2M）→ PAT → CLI プロファイルの順に使う
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { cfg } from "./config.js";
const run = promisify(execFile);
let cache: { token: string; exp: number } | null = null;

export async function workspaceToken(): Promise<string> {
  if (cache && cache.exp - Date.now() > 120_000) return cache.token;
  if (cfg.clientId && cfg.clientSecret) {
    const r = await fetch(`${cfg.host}/oidc/v1/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded",
        Authorization: "Basic " + Buffer.from(`${cfg.clientId}:${cfg.clientSecret}`).toString("base64") },
      body: "grant_type=client_credentials&scope=all-apis",
    });
    if (!r.ok) throw new Error(`OAuth M2M failed: ${r.status} ${await r.text()}`);
    const j: any = await r.json();
    cache = { token: j.access_token, exp: Date.now() + j.expires_in * 1000 };
  } else if (cfg.token) {
    cache = { token: cfg.token, exp: Date.now() + 3600_000 * 24 };
  } else {
    const { stdout } = await run(cfg.cli, ["auth", "token", "-p", cfg.profile || "DEFAULT", "-o", "json"],
      { env: { ...process.env, DATABRICKS_CLI_DO_NOT_EXECUTE_NEWER_VERSION: "1" } });
    const j = JSON.parse(stdout);
    cache = { token: j.access_token, exp: j.expiry ? Date.parse(j.expiry) : Date.now() + 1800_000 };
  }
  return cache.token;
}

export async function api<T = any>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${cfg.host}${path}`, {
    method, headers: { Authorization: `Bearer ${await workspaceToken()}`, "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await r.text();
  if (!r.ok) throw new Error(`${method} ${path} -> ${r.status}: ${text.slice(0, 300)}`);
  return (text ? JSON.parse(text) : {}) as T;
}

let me: string | null = null;
export async function principalName(): Promise<string> {
  if (cfg.clientId) return cfg.clientId; // SP の Postgres ロール名はアプリケーション ID
  if (!me) me = (await api<any>("GET", "/api/2.0/preview/scim/v2/Me")).userName as string;
  return me!;
}
