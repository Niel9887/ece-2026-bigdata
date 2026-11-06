# Polaris deployment lab

The chart uses Polaris 1.8.0 and PostgreSQL. It creates the `dev` and `analyst` principals, their roles, and a catalog pointing to the existing warehouse in S3.

Run from the Onyxia `vscode-pyspark` terminal after checking that the current AWS environment variables can read `bronze/`:

```bash
aws s3 ls "s3://$KUBERNETES_NAMESPACE/bronze/" \
  --endpoint-url "https://$AWS_S3_ENDPOINT"
bash polaris/deploy.sh
```

The script creates Kubernetes secrets for the root password and temporary S3 keys. It keeps the existing root password on later runs and restarts Polaris so it reads updated S3 keys. These values do not belong in Git.

The bootstrap Job returns the `dev` and `analyst` credentials only when it creates those principals. The script saves them in `/home/onyxia/.polaris-credentials.env` with restricted permissions. Copy that file to a safe place outside this temporary service before running the next lab.
