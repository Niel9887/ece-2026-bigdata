SELECT  -- quantity per product and share of the total
  product,
  count(*) AS orders,
  sum(quantity) AS quantity,
  round(100 * sum(quantity) / sum(sum(quantity)) OVER (), 1) AS share_pct  -- window over all the groups
FROM orders
GROUP BY product
ORDER BY quantity DESC;

SELECT date_trunc('month', date) AS month, count(*) AS orders, sum(quantity) AS quantity  -- orders per month
FROM orders
GROUP BY month
ORDER BY month;

SELECT u.username, u.name, count(*) AS orders, sum(o.quantity) AS quantity  -- top 5 customers
FROM orders o
JOIN users u ON o.user_uuid = u.uuid
GROUP BY ALL
ORDER BY quantity DESC
LIMIT 5;

SELECT
  (date_diff('year', u.birthdate, DATE '2020-01-01') // 20) * 20 AS age_group,  -- groups of 20 years
  count(DISTINCT u.uuid) AS users,
  count(*) AS orders,
  round(avg(o.quantity), 2) AS avg_quantity
FROM orders o
JOIN users u ON o.user_uuid = u.uuid
GROUP BY age_group
ORDER BY age_group;

WITH daily AS (  -- quantity per day first
  SELECT date::DATE AS day, sum(quantity) AS quantity
  FROM orders
  GROUP BY day
)
SELECT
  day,
  quantity,
  sum(quantity) OVER (ORDER BY day) AS cumulative,
  round(avg(quantity) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS avg_7d  -- 7-day moving average
FROM daily
ORDER BY day
LIMIT 10;

SELECT strftime(date, '%Y-%m') AS month, product, sum(quantity) AS quantity  -- best product of each month
FROM orders
GROUP BY month, product
QUALIFY rank() OVER (PARTITION BY month ORDER BY sum(quantity) DESC) = 1  -- QUALIFY filters on the window result
ORDER BY month;

PIVOT (SELECT strftime(date, '%Y-%m') AS month, product, quantity FROM orders)  -- one column per product
ON product
USING sum(quantity)
ORDER BY month;
