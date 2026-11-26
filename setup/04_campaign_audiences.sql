CREATE OR REPLACE TABLE main.casio_cx.campaign_audiences (audience_id STRING, audience_name STRING, series STRING, offer STRING, active BOOLEAN)
COMMENT 'アプリで使うオーディエンス（CustomerLake Campaign Agents で Genie から作成）の一覧';
INSERT INTO main.casio_cx.campaign_audiences VALUES
 ('<audience-id-protrek>', 'PRO TREK未保有アウトドア層', 'PRO TREK', '新作 PRW-B1000WM の先行案内と店頭での試着予約', true),
 ('<audience-id-exword>', '電子辞書・学び関心 メール同意者', 'EX-word', '新学期 EX-word 早期購入キャンペーン', true),
 ('<audience-id-oceanus>', 'ビジネス・上質派 高額NPS優良顧客', 'OCEANUS', 'OCEANUS 新作の特別内覧会へのご招待', true);
SELECT a.audience_name, (SELECT count(*) FROM main.audiences.`<audience-id-protrek>`) n1 FROM main.casio_cx.campaign_audiences a LIMIT 1
