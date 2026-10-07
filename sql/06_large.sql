COPY (FROM read_csv(getvariable('bucket') || '/large/orders.csv', strict_mode=false))  -- big csv to parquet
TO (getvariable('bucket') || '/large/orders.parquet') (FORMAT parquet);

SELECT count(*) FROM read_parquet(getvariable('bucket') || '/large/orders.parquet');  -- 252416 rows

SELECT row_group_id, row_group_num_rows, stats_min, stats_max  -- min/max of date in each row group
FROM parquet_metadata(getvariable('bucket') || '/large/orders.parquet')
WHERE path_in_schema = 'date';
