import os
import subprocess

from session import make_spark


bucket = os.environ["KUBERNETES_NAMESPACE"]
spark = make_spark()

spark.sql("DESCRIBE NAMESPACE EXTENDED polaris.silver").show(truncate=False)
source_count = spark.sql("SELECT count(*) AS total FROM lab.silver.users").first()["total"]
tables = {row.tableName for row in spark.sql("SHOW TABLES IN polaris.silver").collect()}
if "users" not in tables:
    # Keep the source table in lab; Polaris writes its own table metadata.
    spark.table("lab.silver.users").writeTo("polaris.silver.users").createOrReplace()

target_count = spark.sql("SELECT count(*) AS total FROM polaris.silver.users").first()["total"]
print("Users in lab:", source_count)
print("Users in Polaris:", target_count)
spark.sql("SHOW TABLES IN polaris.silver").show()
spark.stop()

objects = subprocess.run(
    ["aws", "s3", "--profile", "default", "ls", f"s3://{bucket}/warehouse/silver/", "--recursive"],
    check=True,
    capture_output=True,
    text=True,
).stdout
for line in objects.splitlines():
    if "/users/" in line:
        print(line.split()[-1])

if source_count != target_count:
    raise SystemExit("User counts do not match")
