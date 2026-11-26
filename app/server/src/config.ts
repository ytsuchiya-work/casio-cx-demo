import "dotenv/config";
const env = (k: string, d = "") => (process.env[k] ?? d).trim();
export const cfg = {
  host: ((h) => (h && !/^https?:\/\//.test(h) ? `https://${h}` : h))(env("DATABRICKS_HOST").replace(/\/$/, "")),
  clientId: env("DATABRICKS_CLIENT_ID"),
  clientSecret: env("DATABRICKS_CLIENT_SECRET"),
  token: env("DATABRICKS_TOKEN"),
  profile: env("DATABRICKS_PROFILE"),
  cli: env("DATABRICKS_CLI", "databricks"),
  catalog: env("UC_CATALOG", "main"),
  schema: env("UC_SCHEMA", "casio_cx"),
  serving: env("SERVING_SCHEMA", "casio_cx_serving"),
  warehouseId: env("WAREHOUSE_ID"),
  jobId: Number(env("JOB_ID", "0")),
  lbEndpoint: env("LAKEBASE_ENDPOINT"),
  lbDatabase: env("LAKEBASE_DATABASE", "databricks_postgres"),
  port: Number(env("DATABRICKS_APP_PORT") || env("PORT", "8080")),
};
export const uc = (t: string) => `${cfg.catalog}.${cfg.schema}.${t}`;
export const workspaceUrl = (path: string) => `${cfg.host}${path}`;
