"""Lakebase に Qualtrics 回答の受け皿（OLTP）を作り、過去の回答を投入する。何度実行しても同じ状態になる。"""
import sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lb

DATA = Path(__file__).resolve().parents[1] / "data"
DDL = """
CREATE SCHEMA IF NOT EXISTS survey;
DROP TABLE IF EXISTS survey.responses;
DROP TABLE IF EXISTS survey.respondents;
CREATE TABLE survey.respondents (
  contact_id   text PRIMARY KEY,
  full_name    text NOT NULL,
  email        text,
  phone        text,
  postal_code  text,
  prefecture   text,
  age_band     text,
  gender       text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE survey.responses (
  response_id            text PRIMARY KEY,
  survey_id              text NOT NULL,
  survey_name            text NOT NULL,
  contact_id             text NOT NULL REFERENCES survey.respondents(contact_id),
  submitted_at           timestamptz NOT NULL,
  nps                    smallint CHECK (nps BETWEEN 0 AND 10),
  satisfaction           smallint CHECK (satisfaction BETWEEN 1 AND 5),
  owned_products         text[] NOT NULL DEFAULT '{}',
  interests              text[] NOT NULL DEFAULT '{}',
  next_purchase_category text,
  budget_band            text,
  usage_scenes           text[] NOT NULL DEFAULT '{}',
  comment                text,
  channel                text,
  raw_payload            jsonb,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON survey.responses (contact_id, submitted_at DESC);
-- Lakebase CDF の必須設定（更新前後の全列を WAL に残す）
ALTER TABLE survey.respondents REPLICA IDENTITY FULL;
ALTER TABLE survey.responses   REPLICA IDENTITY FULL;
"""
with lb.connect() as c:
    c.execute(DDL)
    with c.cursor() as cur:
        for tbl, f in [("survey.respondents", "lb_respondents.csv"), ("survey.responses", "lb_responses.csv")]:
            cols = next(csv.reader(open(DATA / f)))
            with cur.copy(f"COPY {tbl} ({','.join(cols)}) FROM STDIN WITH (FORMAT csv, HEADER true)") as cp:
                with open(DATA / f, "rb") as fh:
                    while chunk := fh.read(1 << 16): cp.write(chunk)
            print(tbl, c.execute(f"select count(*) from {tbl}").fetchone()[0])
    c.execute("UPDATE survey.respondents SET updated_at = created_at; UPDATE survey.responses SET created_at = submitted_at, updated_at = submitted_at;")
    print(c.execute("select current_user, version()").fetchone())
