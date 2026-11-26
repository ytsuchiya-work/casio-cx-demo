USE CATALOG main;
CREATE OR REPLACE TABLE casio_cx.products COMMENT 'CASIO 製品マスタ（casio.com/jp 掲載の型番・税込価格）' AS
SELECT product_id, product_name, model, series, category, CAST(price AS INT) AS price, split(tags, ',') AS tags, url
FROM read_files('/Volumes/main/casio_cx/raw/products.csv', format => 'csv', header => true, inferSchema => false);
CREATE OR REPLACE TABLE casio_cx.src_casio_id_members COMMENT 'CASIO ID 会員（架空データ）' AS
SELECT member_id, last_name, first_name, last_name_kana, first_name_kana, email, phone, postal_code, prefecture, city, address_line,
       CAST(birth_date AS DATE) AS birth_date, gender, CAST(registered_at AS TIMESTAMP) AS registered_at, CAST(newsletter_optin AS BOOLEAN) AS newsletter_optin
FROM read_files('/Volumes/main/casio_cx/raw/src_casio_id_members.csv', format => 'csv', header => true, inferSchema => false);
CREATE OR REPLACE TABLE casio_cx.src_online_store_customers COMMENT 'CASIO オンラインストア 顧客（架空データ）' AS
SELECT customer_no, full_name, full_name_kana, email, tel, zip, address, CAST(created_at AS TIMESTAMP) AS created_at
FROM read_files('/Volumes/main/casio_cx/raw/src_online_store_customers.csv', format => 'csv', header => true, inferSchema => false);
CREATE OR REPLACE TABLE casio_cx.online_store_orders COMMENT 'CASIO オンラインストア 注文明細（架空データ）' AS
SELECT order_id, customer_no, product_id, CAST(quantity AS INT) AS quantity, CAST(amount AS INT) AS amount, CAST(order_date AS TIMESTAMP) AS order_date
FROM read_files('/Volumes/main/casio_cx/raw/online_store_orders.csv', format => 'csv', header => true, inferSchema => false);
CREATE OR REPLACE TABLE casio_cx._truth_xref COMMENT '検証用：名寄せの正解（CustomerLake には渡さない）' AS
SELECT * FROM read_files('/Volumes/main/casio_cx/raw/truth_xref.csv', format => 'csv', header => true, inferSchema => false);
CREATE OR REPLACE TABLE casio_cx._persons_truth COMMENT '検証用：架空の人物と真の嗜好' AS
SELECT * FROM read_files('/Volumes/main/casio_cx/raw/persons_truth.csv', format => 'csv', header => true, inferSchema => false);
SELECT 'products' t, count(*) n FROM casio_cx.products UNION ALL SELECT 'members', count(*) FROM casio_cx.src_casio_id_members UNION ALL SELECT 'store', count(*) FROM casio_cx.src_online_store_customers UNION ALL SELECT 'orders', count(*) FROM casio_cx.online_store_orders;
