// Databricks SQL（Statement Execution API）
import { cfg } from "./config.js";
import { api } from "./auth.js";
export async function sql(statement: string, parameters: { name: string; value: string }[] = []): Promise<Record<string, any>[]> {
  let r = await api<any>("POST", "/api/2.0/sql/statements", {
    warehouse_id: cfg.warehouseId, statement, parameters, wait_timeout: "30s", disposition: "INLINE", format: "JSON_ARRAY",
  });
  while (["PENDING", "RUNNING"].includes(r.status?.state)) {
    await new Promise((s) => setTimeout(s, 1000));
    r = await api<any>("GET", `/api/2.0/sql/statements/${r.statement_id}`);
  }
  if (r.status?.state !== "SUCCEEDED") throw new Error(r.status?.error?.message ?? "SQL failed");
  const cols: string[] = (r.manifest?.schema?.columns ?? []).map((c: any) => c.name);
  return (r.result?.data_array ?? []).map((row: any[]) => Object.fromEntries(cols.map((c, i) => [c, row[i]])));
}
