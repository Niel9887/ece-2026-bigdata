import os
import subprocess

from session import make_spark


bucket = os.environ["KUBERNETES_NAMESPACE"]
prefix = f"s3://{bucket}/warehouse/silver/orders/"


def aws(*args):
    return subprocess.run(
        ["aws", "s3", "--profile", "default", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def object_count():
    return len(aws("ls", prefix, "--recursive").splitlines())


version = aws("cp", prefix + "metadata/version-hint.text", "-").strip()
before = object_count()
spark = make_spark()
print("Metadata version:", version)
print("Objects before:", before)

spark.sql("CREATE NAMESPACE IF NOT EXISTS polaris.silver")
tables = {row.tableName for row in spark.sql("SHOW TABLES IN polaris.silver").collect()}
if "orders" not in tables:
    # Register the current metadata file without writing the table again.
    spark.sql(f"""
        CALL polaris.system.register_table(
          table => 'silver.orders',
          metadata_file => 's3a://{bucket}/warehouse/silver/orders/metadata/v{version}.metadata.json'
        )
    """).show()

lab_count = spark.sql("SELECT count(*) AS count FROM lab.silver.orders").first()["count"]
polaris_count = spark.sql("SELECT count(*) AS count FROM polaris.silver.orders").first()["count"]
after = object_count()
print("Orders in lab:", lab_count)
print("Orders in Polaris:", polaris_count)
print("Objects after:", after)
spark.sql("SHOW TABLES IN polaris.silver").show()
spark.sql("SELECT snapshot_id, operation, committed_at FROM polaris.silver.orders.snapshots").show(truncate=False)
spark.stop()

if lab_count != polaris_count or before != after:
    raise SystemExit("Counts changed during registration")
