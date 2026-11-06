#!/usr/bin/env bash
set -euo pipefail
set +x
umask 077

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
chart="$repo_dir/polaris/deployment"
bucket="${KUBERNETES_NAMESPACE:?KUBERNETES_NAMESPACE is missing}"
: "${AWS_S3_ENDPOINT:?AWS_S3_ENDPOINT is missing}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is missing}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is missing}"
: "${AWS_SESSION_TOKEN:?AWS_SESSION_TOKEN is missing}"

kubectl create configmap polaris-config \
  --from-literal=POLARIS_CATALOG="$bucket" \
  --from-literal=POLARIS_URI=http://polaris:8181 \
  --from-literal=POLARIS_MGMT_URI=http://polaris-mgmt:8182 \
  --from-literal=POLARIS_REALM=POLARIS \
  --from-literal=POLARIS_CLIENT_ID=root \
  --from-literal=POLARIS_BASE_LOCATION="s3://$bucket/warehouse/" \
  --from-literal=S3_ENDPOINT="https://$AWS_S3_ENDPOINT" \
  --dry-run=client -o yaml | kubectl apply -f -

if kubectl get secret polaris-credential >/dev/null 2>&1; then
  bootstrap_key="$(kubectl get secret polaris-credential \
    -o jsonpath='{.data.POLARIS_BOOTSTRAP_CREDENTIALS}')"
  if [ -z "$bootstrap_key" ]; then
    root_password="$(kubectl get secret polaris-credential \
      -o jsonpath='{.data.POLARIS_ROOT_SECRET}' | base64 -d)"
    kubectl create secret generic polaris-credential \
      --from-literal=POLARIS_ROOT_SECRET="$root_password" \
      --from-literal=POLARIS_BOOTSTRAP_CREDENTIALS="POLARIS,root,$root_password" \
      --dry-run=client -o yaml | kubectl apply -f -
    unset root_password
  fi
else
  root_password="$(openssl rand -hex 16)"
  kubectl create secret generic polaris-credential \
    --from-literal=POLARIS_ROOT_SECRET="$root_password" \
    --from-literal=POLARIS_BOOTSTRAP_CREDENTIALS="POLARIS,root,$root_password" \
    --dry-run=client -o yaml | kubectl apply -f -
  unset root_password
fi

kubectl create secret generic polaris-s3 \
  --from-literal=AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  --from-literal=AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

helm dependency update "$chart"
helm upgrade --install polaris "$chart" --wait --timeout 10m

job_log="$(kubectl logs job/polaris-bootstrap)"
credentials="$(printf '%s\n' "$job_log" \
  | awk '/"credentials"/' \
  | jq -r 'select(.principal == "dev" or .principal == "analyst")
      | "POLARIS_\(.principal | ascii_upcase)_CREDENTIAL=\"\(.credentials.clientId):\(.credentials.clientSecret)\""')"
if [ -n "$credentials" ]; then
  printf '%s\n' "$credentials" > "$HOME/.polaris-credentials.env"
  chmod 600 "$HOME/.polaris-credentials.env"
  echo 'Saved the new principal credentials outside the repository.'
fi
unset job_log credentials

kubectl rollout restart deployment/polaris
kubectl rollout status deployment/polaris
curl -fsS http://polaris-mgmt:8182/q/health
