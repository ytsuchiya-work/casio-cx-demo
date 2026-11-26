#!/usr/bin/env bash
# CDF を確実に開始させるため、Lakebase コンピュートを1回停止→再開させる（自動停止を一時的に60秒に）
set -euo pipefail
export DATABRICKS_CLI_DO_NOT_EXECUTE_NEWER_VERSION=1
D=databricks; P=${DATABRICKS_PROFILE:-DEFAULT}
EP=projects/${LB_PROJECT:-casio-cx-demo}/branches/production/endpoints/primary
ORIG=$($D postgres get-endpoint $EP -p $P -o json | jq -r '.status.suspend_timeout_duration')
set_s() { $D postgres update-endpoint $EP spec.suspend_timeout_duration --json "{\"spec\":{\"suspend_timeout_duration\":\"$1\"}}" -p $P -o json >/dev/null; }
set_s 60s
for i in $(seq 1 90); do S=$($D postgres get-endpoint $EP -p $P -o json | jq -r .status.current_state); [ "$S" != ACTIVE ] && break; sleep 10; done
set_s "$ORIG"; echo "state=$S restored suspend=$ORIG"
