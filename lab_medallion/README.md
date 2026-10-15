# dbt medallion lab

This dbt project reads bronze CSV files from S3 and builds the silver models as DuckDB views. The silver views can also be exported to Parquet under `silver/dbt/` in S3.

Run commands from this directory. Set `LAB_BUCKET_NAME` to the Onyxia bucket name first.

```bash
uv run dbt debug
uv run dbt build
uv run dbt docs generate --static
```
