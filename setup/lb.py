"""Lakebase 接続ヘルパー（ユーザー本人の OAuth トークンをパスワードに使う）"""
import json, subprocess, functools, time, os
import psycopg

DBX = "databricks"
PROFILE = os.environ.get("DATABRICKS_PROFILE", "DEFAULT")
PROJECT = os.environ.get("LB_PROJECT", "casio-cx-demo")
EP = f"projects/{PROJECT}/branches/production/endpoints/primary"
PGDB = "databricks_postgres"
ENV = dict(os.environ, DATABRICKS_CLI_DO_NOT_EXECUTE_NEWER_VERSION="1")

def _run(*a):
    r = subprocess.run([DBX, *a, "-p", PROFILE, "-o", "json"], capture_output=True, text=True, env=ENV)
    if r.returncode: raise RuntimeError(r.stderr)
    return json.loads(r.stdout)

@functools.lru_cache(maxsize=1)
def host(): return _run("postgres", "get-endpoint", EP)["status"]["hosts"]["host"]
@functools.lru_cache(maxsize=1)
def user(): return _run("current-user", "me")["userName"]
_tok = {"v": None, "t": 0}
def token():
    if not _tok["v"] or time.time() - _tok["t"] > 2400:
        _tok["v"] = _run("postgres", "generate-database-credential", EP)["token"]; _tok["t"] = time.time()
    return _tok["v"]
def connect(autocommit=True):
    return psycopg.connect(host=host(), user=user(), dbname=PGDB, password=token(), sslmode="require", autocommit=autocommit)
