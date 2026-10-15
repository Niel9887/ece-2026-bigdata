# dbt medallion lab

This dbt project reads bronze CSV files from S3 and writes the silver and monthly gold models as Parquet files.

Run commands from this directory. Set `LAB_BUCKET_NAME` to the Onyxia bucket name first.

```bash
uv run dbt debug
uv run dbt build
uv run dbt docs generate --static
```
