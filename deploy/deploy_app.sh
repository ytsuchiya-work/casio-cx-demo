#!/usr/bin/env bash
# Databricks Apps へデプロイ：ビルド → ビルド済み一式を deploy/app に集める → ワークスペースへ上げて apps deploy
set -euo pipefail
cd "$(dirname "$0")/.."
export DATABRICKS_CLI_DO_NOT_EXECUTE_NEWER_VERSION=1
D=${DATABRICKS_CLI:-databricks}; P=${DATABRICKS_PROFILE:-DEFAULT}
APP=${APP_NAME:-casio-cx-demo}; WS=/Workspace/Users/$($D current-user me -p $P -o json | jq -r .userName)/casio-cx-demo/app
(cd app && npm run build)
rm -rf deploy/app/server/dist deploy/app/web/dist; mkdir -p deploy/app/server deploy/app/web
cp -R app/server/dist deploy/app/server/dist; cp -R app/web/dist deploy/app/web/dist
$D workspace import-dir deploy/app "$WS" --overwrite -p $P >/dev/null
$D apps deploy "$APP" --source-code-path "$WS" -p $P -o json | jq -c '.status'
$D apps get "$APP" -p $P -o json | jq -r .url
