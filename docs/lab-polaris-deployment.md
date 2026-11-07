# Polaris deployment lab

## Deploy Polaris

I set the `vscode-pyspark` memory limit to 2500Mi and stopped the older VS Code service to stay within the 4Gi memory quota. The S3 `default` profile could read `bronze/` after I refreshed its temporary credentials.

The first Helm install could not create PostgreSQL's 1Gi volume because the namespace had already used its 20Gi storage quota. I used the existing volume of the stopped service instead. PostgreSQL stores its data in the `polaris-postgresql` subdirectory.

```bash
POLARIS_DB_PVC=vscode-pyspark-180390 bash polaris/deploy.sh
```

## Check the deployment

Helm reported `deployed`. The PostgreSQL and Polaris pods were both `1/1 Running`, and the `polaris-bootstrap` Job completed. The management health endpoint returned `UP`, and the job reported that the `user-n-raluy-ece` catalog was ready.

The script saved the `dev` and `analyst` credentials in `/home/onyxia/.polaris-credentials.env` with mode `600`. I kept this file outside the Git repository.
