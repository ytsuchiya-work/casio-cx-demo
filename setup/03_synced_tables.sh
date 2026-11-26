#!/usr/bin/env bash
# Lakehouse の集計テーブル → Lakebase（同期テーブル、Snapshot、LTAP Direct Writes = accelerated_sync）
set -euo pipefail
export DATABRICKS_CLI_DO_NOT_EXECUTE_NEWER_VERSION=1
D=databricks; P=${DATABRICKS_PROFILE:-DEFAULT}
CAT=main; SRC=$CAT.casio_cx; DST=$CAT.casio_cx_serving
BR=projects/casio-cx-demo/branches/production
mk() { # dest source pk_json
  $D postgres create-synced-table "$DST.$1" --no-wait -p $P -o json --json "{\"spec\":{\"source_table_full_name\":\"$SRC.$2\",\"primary_key_columns\":$3,
    \"scheduling_policy\":\"SNAPSHOT\",\"accelerated_sync\":true,\"branch\":\"$BR\",\"postgres_database\":\"databricks_postgres\"}}" | jq -c '{name: .name, done: .done}' || true
}
# products / customers は UI で作成済み（同じ設定）
mk recommendations   gold_recommendations   '["profile_id","rank"]'
mk segment_summary   gold_segment_summary   '["segment"]'
mk topic_summary     gold_topic_summary     '["segment","topic"]'
mk campaign_members  gold_campaign_members  '["profile_id","audience_id"]'
mk contact_profile   gold_contact_profile   '["contact_id"]'
