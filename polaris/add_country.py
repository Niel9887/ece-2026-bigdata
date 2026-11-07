import os
import subprocess

from session import make_spark


bucket = os.environ["KUBERNETES_NAMESPACE"]
metadata_path = f"s3://{bucket}/warehouse/silver/users/metadata/"


def metadata_files():
    output = subprocess.run(
        ["aws", "s3", "--profile", "default", "ls", metadata_path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {line.split()[-1] for line in output.splitlines() if line.endswith("metadata.json")}


spark = make_spark()
before_files = metadata_files()
before_snapshots = spark.sql("SELECT count(*) AS total FROM polaris.silver.users.snapshots").first()["total"]
columns = {row.col_name for row in spark.sql("DESCRIBE polaris.silver.users").collect()}
if "country" not in columns:
    spark.sql("ALTER TABLE polaris.silver.users ADD COLUMN country STRING")

spark.sql("DESCRIBE polaris.silver.users").show(truncate=False)
after_snapshots = spark.sql("SELECT count(*) AS total FROM polaris.silver.users.snapshots").first()["total"]
after_files = metadata_files()
print("Metadata files added:", sorted(after_files - before_files))
print("Snapshots before:", before_snapshots)
print("Snapshots after:", after_snapshots)
spark.stop()
