"""SQL ウェアハウスで文を1つずつ実行する（Statement Execution API）。usage: python sql.py file.sql | -e "SQL" """
import sys, os, time, re
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
w = WorkspaceClient(profile=os.environ.get("DATABRICKS_PROFILE", "DEFAULT"))
WH = os.environ.get("WAREHOUSE_ID", "<warehouse-id>")
def run(stmt, show=True):
    r = w.statement_execution.execute_statement(warehouse_id=WH, statement=stmt, wait_timeout="50s")
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2); r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state != StatementState.SUCCEEDED:
        raise SystemExit(f"FAILED: {stmt[:200]}\n{r.status.error.message}")
    rows = (r.result.data_array or []) if r.result else []
    cols = [c.name for c in r.manifest.schema.columns] if r.manifest and r.manifest.schema and r.manifest.schema.columns else []
    if show and rows:
        print(" | ".join(cols)); [print(" | ".join("" if v is None else str(v) for v in row)) for row in rows[:50]]
    return cols, rows
def split(sql):
    sql = re.sub(r"--[^\n]*", "", sql)
    return [s.strip() for s in sql.split(";\n") if s.strip().strip(";")]
if __name__ == "__main__":
    if sys.argv[1] == "-e": stmts = [sys.argv[2]]
    else: stmts = split(open(sys.argv[1]).read())
    for s in stmts:
        t = time.time(); run(s.rstrip(";")); print(f"-- ok ({time.time()-t:.1f}s): {s.splitlines()[0][:90]}")
