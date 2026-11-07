#!/usr/bin/env bash
set -euo pipefail
set +x
umask 077

bucket="${KUBERNETES_NAMESPACE:?}"
api="http://polaris:8181/api/management/v1"
catalog="$api/catalogs/$bucket"
root_secret="$(kubectl get secret polaris-credential -o jsonpath='{.data.POLARIS_ROOT_SECRET}' | base64 -d)"
token="$(curl -fsS -u "root:$root_secret" -H 'Polaris-Realm: POLARIS' \
  -d 'grant_type=client_credentials' -d 'scope=PRINCIPAL_ROLE:ALL' \
  http://polaris:8181/api/catalog/v1/oauth/tokens | jq -er '.access_token')"
unset root_secret

request() {
  curl -fsS -H "Authorization: Bearer $token" -H 'Polaris-Realm: POLARIS' \
    -H 'Content-Type: application/json' "$@"
}

status() {
  curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $token" \
    -H 'Polaris-Realm: POLARIS' "$1"
}

if [ "$(status "$api/principals/silver_tester")" = 404 ]; then
  response="$(request -X POST -d '{"principal":{"name":"silver_tester","properties":{}},"credentialRotationRequired":false}' "$api/principals")"
  printf 'POLARIS_SILVER_TEST_CREDENTIAL="%s:%s"\n' \
    "$(jq -r '.credentials.clientId' <<< "$response")" \
    "$(jq -r '.credentials.clientSecret' <<< "$response")" \
    > /home/onyxia/.polaris-silver-reader.env
  chmod 600 /home/onyxia/.polaris-silver-reader.env
fi

if [ "$(status "$api/principal-roles/silver_test_role")" = 404 ]; then
  request -X POST -d '{"principalRole":{"name":"silver_test_role","properties":{}}}' \
    "$api/principal-roles" >/dev/null
fi

if [ "$(status "$catalog/catalog-roles/silver_reader")" = 404 ]; then
  request -X POST -d '{"catalogRole":{"name":"silver_reader","properties":{}}}' \
    "$catalog/catalog-roles" >/dev/null
fi

grant() {
  local scope="$1" privilege="$2" body
  if [ "$scope" = catalog ]; then
    body="$(jq -nc --arg privilege "$privilege" '{grant:{type:"catalog",privilege:$privilege}}')"
  else
    body="$(jq -nc --arg privilege "$privilege" \
      '{grant:{type:"namespace",namespace:["silver"],privilege:$privilege}}')"
  fi
  if ! request "$catalog/catalog-roles/silver_reader/grants" | jq -e \
    --arg scope "$scope" --arg privilege "$privilege" \
    '.grants[]? | select(.type == $scope and .privilege == $privilege)' >/dev/null; then
    request -X PUT -d "$body" "$catalog/catalog-roles/silver_reader/grants" >/dev/null
  fi
}

grant catalog CATALOG_READ_PROPERTIES
grant namespace NAMESPACE_LIST
grant namespace NAMESPACE_READ_PROPERTIES
grant namespace TABLE_READ_DATA
grant namespace TABLE_READ_PROPERTIES

request -X PUT -d '{"principalRole":{"name":"silver_test_role"}}' \
  "$api/principals/silver_tester/principal-roles" >/dev/null
request -X PUT -d '{"catalogRole":{"name":"silver_reader"}}' \
  "$api/principal-roles/silver_test_role/catalog-roles/$bucket" >/dev/null

echo 'silver_tester has read privileges on silver'
