SELECT  -- exercise 1
  round((SELECT count(*) FROM orders) / (SELECT count(*) FROM users), 2) AS avg_orders_per_user,
  round(avg(quantity), 2) AS avg_quantity_per_order
FROM orders;

SELECT  -- exercise 2
  u.username,
  min(o.date)::DATE AS first_order,
  max(o.date)::DATE AS last_order,
  date_diff('day', min(o.date)::DATE, max(o.date)::DATE) AS days_between
FROM users u
LEFT JOIN orders o ON o.user_uuid = u.uuid  -- left join so a user with no order still shows up
GROUP BY u.uuid, u.username
ORDER BY first_order, u.username;

SELECT hour(date) AS hour, sum(quantity) AS quantity  -- exercise 3, hour in UTC (set in init.sql)
FROM orders
GROUP BY hour
ORDER BY quantity DESC
LIMIT 3;

WITH monthly AS (  -- exercise 4, quantity per product and month
  SELECT product, strftime(date, '%Y-%m') AS month, sum(quantity) AS quantity
  FROM orders
  GROUP BY product, month
),
with_previous AS (
  SELECT
    product,
    month,
    quantity,
    lag(quantity) OVER (PARTITION BY product ORDER BY month) AS previous_quantity  -- value of the month before
  FROM monthly
)
SELECT
  product,
  month,
  quantity,
  previous_quantity,
  round(100 * (quantity - previous_quantity) / previous_quantity, 1) AS variation_pct
FROM with_previous
ORDER BY product, month;

SELECT u.username, count(DISTINCT o.product) AS products  -- exercise 5
FROM orders o
JOIN users u ON o.user_uuid = u.uuid
GROUP BY u.uuid, u.username
HAVING count(DISTINCT o.product) = (SELECT count(DISTINCT product) FROM orders)  -- all 6 products
ORDER BY u.username;

SELECT u.username, count(*) AS orders  -- the 5 users who miss a product
FROM orders o
JOIN users u ON o.user_uuid = u.uuid
GROUP BY u.uuid, u.username
HAVING count(DISTINCT o.product) < (SELECT count(DISTINCT product) FROM orders)
ORDER BY orders;
