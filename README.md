# casio-cx-demo

アンケート収集アプリと分析の E2E デモ。Qualtrics（想定）のアンケート回答を Lakebase に保存し、Lakebase CDF で Lakehouse に連携、
Lakehouse で AI 分類・集計した結果を同期テーブル（LTAP Direct Writes）で Lakebase に戻して、React アプリで顧客ごとのおすすめを表示します。
名寄せとキャンペーン対象者づくりには CustomerLake（Profile Agents / Campaign Agents）を使います。

- データはすべて架空です。製品名・型番・価格は casio.com/jp の掲載内容（2026年11月25日時点）を参考にしています
- CustomerLake は Beta／Private Preview の機能です。仕様が変わる場合があります
- 説明資料：[docs/casio-cx-demo-slides.pdf](docs/casio-cx-demo-slides.pdf)（アプリの概要・使用技術・アーキテクチャ・デモの説明・Databricks を使う価値・まとめ）

```
Qualtrics（Webhook）
   │  POST /api/qualtrics/webhook
   ▼
React + Node.js アプリ ──INSERT──▶ Lakebase（Postgres）survey.respondents / survey.responses
   ▲                                    │ Lakebase CDF
   │                                    ▼
   │                       Unity Catalog: casio_cx.lb_responses_history（Delta）
   │                                    │ Lakeflow ジョブ（サーバーレス）
   │                                    │  01 準備 → 02 AI 分類（モデルサービス）→ 03 顧客360・集計
   │                                    │  → 05 キャンペーン・推薦（CustomerLake オーディエンス）→ 04 同期
   │            CustomerLake Profile Agents（名寄せ）／Campaign Agents（オーディエンス）
   │                                    │ 同期テーブル（Snapshot + LTAP Direct Writes）
   └──────────SELECT──────────── Lakebase casio_cx_serving.*（recommendations ほか）
```

## フォルダ

| パス | 内容 |
|---|---|
| `app/` | React（TypeScript）＋ Node.js（Express, TypeScript）のアプリ。上部にデータの流れとタイムラインを SSE でリアルタイム表示 |
| `jobs/` | Lakeflow ジョブのノートブック（準備・AI 分類・顧客360・推薦・Lakebase 同期） |
| `setup/` | 架空データ生成、Lakehouse／Lakebase のセットアップ、同期テーブル作成、ジョブ定義、通し試験、リセット |
| `deploy/` | Databricks Apps へのデプロイ用（`app.yaml`、依存だけの `package.json`、`deploy_app.sh`） |
| `video/` | 実アプリの録画とナレーション付き動画の組み立て（Playwright＋ffmpeg） |
| `docs/` | 説明スライド（PDF） |

## セットアップ（概要）

前提：Databricks CLI でログイン済みのプロファイル、Unity Catalog のカタログ（例は `main`）、SQL ウェアハウス、Lakebase（Autoscaling）が使えるワークスペース、CustomerLake のプレビュー。

1. 架空データを作る：`python setup/gen_data.py`（`data/` に CSV ができる）
2. Lakehouse のソース表：CSV を UC ボリューム `casio_cx.raw` に置き、`python setup/sql.py setup/01_uc_sources.sql`
3. Lakebase：プロジェクト `casio-cx-demo` を作成し `python setup/02_lakebase_setup.py`（回答テーブル作成・過去回答の投入・REPLICA IDENTITY FULL）
4. Lakebase CDF：`databricks postgres create-cdf-config <branch>/databases/databricks-postgres <catalog> casio_cx survey --cdf-config-id survey_feed`。同期が始まらない時は `setup/restart_compute.sh`
5. モデルサービス：`casio_cx.survey_classifier`（このデモは Claude Haiku 4.5。思考の多いモデルは出力トークン/分の上限に当たりやすい）
6. ジョブ：`jobs/*.py` をワークスペースに置き、`setup/job.json` の `<you@example.com>` を直して `databricks jobs create --json @setup/job.json`
7. CustomerLake：Identity Project（ソース＝`src_casio_id_members`・`src_online_store_customers`・`src_survey_respondents`、出力＝`casio_cx_idr`）、エンティティ（`gold_customer_360`）、オーディエンス（Genie で作成）を作り、`setup/04_campaign_audiences.sql` の ID を置き換えて登録
8. 同期テーブル：`setup/03_synced_tables.sh`（API では `"accelerated_sync": true` が LTAP Direct Writes）

## アプリを動かす

```bash
cd app
cp .env.example .env        # ワークスペース・ウェアハウス・ジョブ・Lakebase を設定
npm ci
npm run build && npm start  # http://localhost:8080
```

- **ローカル**：`DATABRICKS_PROFILE` に CLI のプロファイル名
- **AWS EC2**：サービスプリンシパルの `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET`（OAuth M2M）。`docker build -t casio-cx-demo ./app && docker run -p 8080:8080 --env-file app/.env casio-cx-demo`
- **Databricks Apps**：`deploy/app/app.yaml` の値を設定して `./deploy/deploy_app.sh`。アプリの SP に、Lakebase のロール（`databricks postgres create-role`）と survey／casio_cx_serving の権限、UC の読み取り、ウェアハウス CAN_USE、ジョブ CAN_MANAGE_RUN を付ける

## デモの進め方

1. ①で顧客を選び「回答例：登山を始めた」を選んで送信
2. 上部のタイムラインで、Lakebase 保存 → CDF → ジョブ5タスク → 同期 → アプリ反映 を追う（検証環境では約2分40秒）
3. ②でおすすめの変化（NEW 表示・理由・キャンペーン）を確認、③で AI 分類の集計、④で CustomerLake の名寄せと対象者数を確認
4. 終わったら `python setup/05_reset_demo.py`（アプリから送った回答を消してジョブを再実行）

通し試験：`python setup/e2e_test.py <profile_id>`（Databricks Apps に対しては `APP_URL` と `APP_TOKEN` を設定）

## 検証環境での実測（AWS 東京）

| 区間 | 時間 |
|---|---|
| Lakebase への INSERT | 41 ms |
| CDF で Delta に到着 | 6〜18 秒 |
| ジョブ（準備・AI 分類・顧客360・推薦・同期） | 36・17・32・17・45 秒 |
| 回答送信からおすすめ更新まで | 約 157〜164 秒 |

名寄せ（Profile Agents）：5,993 件 → 3,048 人。検証用の正解と照合して、1人が1つのプロファイルにまとまった割合 95.3%、別人が混ざったプロファイル 7 件。
