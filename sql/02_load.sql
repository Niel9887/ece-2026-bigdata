CREATE OR REPLACE TABLE users AS  -- copy of the csv in the duckdb file
FROM read_csv(getvariable('bucket') || '/bronze/users.csv');
CREATE OR REPLACE TABLE orders AS
FROM read_csv(getvariable('bucket') || '/bronze/orders.csv');

SELECT
  (SELECT count(*) FROM users) AS users,  -- 50
  (SELECT count(*) FROM orders) AS orders;  -- 2829
SELECT min(date) AS first_order, max(date) AS last_order FROM orders;

SELECT count(*) AS orphan_orders  -- orders with an unknown user, should be 0
FROM orders o
ANTI JOIN users u ON o.user_uuid = u.uuid;

SELECT count(*) AS inactive_users  -- users with no order, should be 0
FROM users u
ANTI JOIN orders o ON o.user_uuid = u.uuid;

SELECT uuid, count(*) AS occurrences  -- duplicated order uuids, should return nothing
FROM orders
GROUP BY uuid
HAVING count(*) > 1;
