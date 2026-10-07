#!/bin/bash
for query in \
  "FROM read_csv(getvariable('bucket') || '/large/orders.csv', strict_mode=false) SELECT product, sum(quantity) GROUP BY product" \
  "FROM read_parquet(getvariable('bucket') || '/large/orders.parquet') SELECT product, sum(quantity) GROUP BY product" \
  "FROM read_parquet(getvariable('bucket') || '/large/orders.parquet') SELECT count(*) WHERE date >= '2100-01-01'" \
  "FROM read_csv('orders_large.csv', strict_mode=false) SELECT product, sum(quantity) GROUP BY product"  # same query on the local file, no network
do
  echo "$query"
  duckdb -init init.sql -c "SET enable_external_file_cache = false; EXPLAIN ANALYZE $query" 2>/dev/null \
  | grep -E 'in:|#GET|Total Time'  # new duckdb process each time so nothing is cached
done
