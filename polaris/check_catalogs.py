import os

from session import make_spark


spark = make_spark()
print("Polaris principal:", os.environ.get("POLARIS_PRINCIPAL", "dev"))
print("S3 implementation:", spark.sparkContext.getConf().get("spark.hadoop.fs.s3.impl"))
for catalog in ("lab", "polaris"):
    print("Namespaces in", catalog)
    spark.sql(f"SHOW NAMESPACES IN {catalog}").show()

spark.stop()
