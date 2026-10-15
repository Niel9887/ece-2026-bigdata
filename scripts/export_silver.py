import os
from pathlib import Path

import duckdb


def main():
    bucket = os.environ.get("LAB_BUCKET_NAME")
    output_root = os.environ.get("LAB_SILVER_ROOT")
    if not output_root:
        if not bucket:
            raise SystemExit("Set LAB_BUCKET_NAME before exporting to S3.")
        output_root = f"s3://{bucket}/silver/dbt"

    database = Path(__file__).resolve().parents[1] / "lab_medallion/lab_medallion.duckdb"
    with duckdb.connect(str(database)) as connection:
        for name in ("users", "orders"):
            path = f"{output_root}/{name}.parquet"
            quoted_path = path.replace("'", "''")
            connection.execute(
                f"COPY (SELECT * FROM main_silver.stg_{name}) "
                f"TO '{quoted_path}' (FORMAT parquet)"
            )
            print(path)


if __name__ == "__main__":
    main()
