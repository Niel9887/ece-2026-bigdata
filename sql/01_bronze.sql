SELECT uuid, username, name, birthdate  -- first 3 users, read on S3 without loading the file
FROM read_csv(
  getvariable('bucket') || '/bronze/users.csv',
  header = true,
  strict_mode = false)
LIMIT 3;

SELECT Delimiter, Quote, HasHeader
FROM sniff_csv(getvariable('bucket') || '/bronze/users.csv');

DESCRIBE FROM read_csv(getvariable('bucket') || '/bronze/orders.csv');  -- types guessed for orders

SELECT column_name, column_type, approx_unique, null_percentage  -- approx_unique is only an estimate
FROM (SUMMARIZE FROM read_csv(getvariable('bucket') || '/bronze/orders.csv'));

SELECT count(DISTINCT uuid) AS uuid, count(DISTINCT user_uuid) AS user_uuid  -- exact values: 2829 and 50
FROM read_csv(getvariable('bucket') || '/bronze/orders.csv');
