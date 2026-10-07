COPY orders TO (getvariable('bucket') || '/analytics/orders.parquet') (FORMAT parquet);  -- export to parquet on S3

SELECT path_in_schema, type, compression, total_compressed_size, total_uncompressed_size  -- footer, one row per column chunk
FROM parquet_metadata(getvariable('bucket') || '/analytics/orders.parquet');

COPY orders TO (getvariable('bucket') || '/analytics/orders_by_product') (FORMAT parquet, PARTITION_BY (product));  -- one folder per product
SELECT file FROM glob(getvariable('bucket') || '/analytics/orders_by_product/**');

EXPLAIN ANALYZE  -- TABLE_SCAN shows Scanning Files: 1/6
SELECT count(*)
FROM read_parquet(getvariable('bucket') || '/analytics/orders_by_product/*/*.parquet')
WHERE product = 'cookie';
