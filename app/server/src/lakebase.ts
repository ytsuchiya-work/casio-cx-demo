// Lakebase（Postgres）接続。パスワードには Databricks が発行する短期の OAuth トークンを使う
import pg from "pg";
import { cfg } from "./config.js";
import { api, principalName } from "./auth.js";

let host = "";
let cred: { token: string; exp: number } | null = null;
async function lbToken() {
  if (cred && cred.exp - Date.now() > 300_000) return cred.token;
  const r = await api<any>("POST", "/api/2.0/postgres/credentials", { endpoint: cfg.lbEndpoint });
  cred = { token: r.token, exp: r.expire_time ? Date.parse(r.expire_time) : Date.now() + 3600_000 };
  return cred.token;
}
let pool: pg.Pool | null = null;
async function getPool() {
  if (pool) return pool;
  if (!host) host = (await api<any>("GET", `/api/2.0/postgres/${cfg.lbEndpoint}`)).status.hosts.host;
  pool = new pg.Pool({
    host, port: 5432, database: cfg.lbDatabase, user: await principalName(), password: lbToken,
    ssl: { rejectUnauthorized: true }, max: 8, idleTimeoutMillis: 60_000,
  });
  pool.on("error", (e) => console.error("pg pool error", e.message));
  return pool;
}
export async function q<T = any>(sql: string, params: unknown[] = []): Promise<T[]> {
  const p = await getPool();
  return (await p.query(sql, params)).rows as T[];
}
export const lakebaseHost = () => host;
