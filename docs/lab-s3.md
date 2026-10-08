# S3 lab

### Why are the credentials stored in a Secret and not in the ConfigMap?

The access keys are sensitive, and Kubernetes keeps sensitive data in a Secret, while a ConfigMap holds plain configuration like the endpoint and the bucket name in `s3-config`. A Secret can be encrypted at rest, but by default it is only base64-encoded, so anyone who can read Secrets in the namespace can still decode the keys.

### The credentials of Onyxia are temporary. What happens if the Job is executed again tomorrow? How would a production platform provide credentials to a Job?

The Job would fail: the session token copied into the Secret has expired, so `aws s3 cp` fails with an `ExpiredToken` error, and Kubernetes retries the pod up to 2 times (`backoffLimit: 2`) before marking the Job as failed. On a production platform the application gets its own credentials from the platform. With Rook, an `ObjectBucketClaim` in the manifests makes the operator create the bucket, a Secret with its credentials and a ConfigMap with the endpoint and bucket name, and the pod receives them as environment variables.

### How would you turn this Job into a daily ingestion?

I would use a CronJob with the same pod template and the schedule `0 2 * * *`, so it runs every day at 2 AM. Each run writes to a key with the date, for example `bronze/orders/$(date +%F).csv`, so the previous days are kept. The CronJob also needs credentials from the platform, as in the previous answer, because the Onyxia token would expire after the first day.
