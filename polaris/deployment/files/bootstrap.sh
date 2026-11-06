#!/bin/sh
set -eu

apk add --no-cache curl jq >/dev/null

API="${POLARIS_URI%/}/api/management/v1"
TOKEN_URL="${POLARIS_URI%/}/api/catalog/v1/oauth/tokens"

attempt=0
until curl -fsS "${POLARIS_MGMT_URI%/}/q/health/ready" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -lt 60 ] || exit 1
  sleep 5
done

TOKEN=$(curl -fsS -u "${POLARIS_CLIENT_ID}:${POLARIS_ROOT_SECRET}" \
  -H "Polaris-Realm: ${POLARIS_REALM}" \
  -d 'grant_type=client_credentials' -d 'scope=PRINCIPAL_ROLE:ALL' \
  "$TOKEN_URL" | jq -er '.access_token')

get() {
  curl -fsS -H "Authorization: Bearer $TOKEN" \
    -H "Polaris-Realm: $POLARIS_REALM" "$1"
}

status() {
  curl -sS -o /dev/null -w '%{http_code}' \
    -H "Authorization: Bearer $TOKEN" \
    -H "Polaris-Realm: $POLARIS_REALM" "$1"
}

post() {
  curl -fsS -X POST -H "Authorization: Bearer $TOKEN" \
    -H "Polaris-Realm: $POLARIS_REALM" \
    -H 'Content-Type: application/json' -d "$2" "$1"
}

put() {
  curl -fsS -X PUT -H "Authorization: Bearer $TOKEN" \
    -H "Polaris-Realm: $POLARIS_REALM" \
    -H 'Content-Type: application/json' -d "$2" "$1"
}

for name in dev analyst; do
  case "$(status "$API/principals/$name")" in
    200) echo "Principal $name already exists" ;;
    404)
      response=$(post "$API/principals" "$(jq -nc --arg name "$name" \
        '{principal:{name:$name,properties:{}},credentialRotationRequired:false}')")
      # The API returns these credentials only when the principal is created.
      echo "$response" | jq -c '{principal:.principal.name,credentials:.credentials}'
      ;;
    *) echo "Cannot check principal $name" >&2; exit 1 ;;
  esac
done

for name in data_engineer data_analyst; do
  case "$(status "$API/principal-roles/$name")" in
    200) : ;;
    404) post "$API/principal-roles" "$(jq -nc --arg name "$name" \
      '{principalRole:{name:$name,properties:{}}}')" >/dev/null ;;
    *) echo "Cannot check principal role $name" >&2; exit 1 ;;
  esac
done

catalog_url="$API/catalogs/$POLARIS_CATALOG"
case "$(status "$catalog_url")" in
  200) : ;;
  404)
    catalog=$(jq -nc --arg name "$POLARIS_CATALOG" \
      --arg location "$POLARIS_BASE_LOCATION" \
      --arg endpoint "$S3_ENDPOINT" --arg region "$AWS_REGION" \
      '{catalog:{name:$name,type:"INTERNAL",
        properties:{"default-base-location":$location},
        storageConfigInfo:{storageType:"S3",allowedLocations:[$location],
          endpoint:$endpoint,endpointInternal:$endpoint,
          pathStyleAccess:true,region:$region,stsUnavailable:true}}}')
    post "$API/catalogs" "$catalog" >/dev/null
    ;;
  *) echo 'Cannot check catalog' >&2; exit 1 ;;
esac

for name in catalog_contributor catalog_reader; do
  role_url="$catalog_url/catalog-roles/$name"
  case "$(status "$role_url")" in
    200) : ;;
    404) post "$catalog_url/catalog-roles" "$(jq -nc --arg name "$name" \
      '{catalogRole:{name:$name,properties:{}}}')" >/dev/null ;;
    *) echo "Cannot check catalog role $name" >&2; exit 1 ;;
  esac
done

grant() {
  url="$catalog_url/catalog-roles/$1/grants"
  if get "$url" | jq -e --arg privilege "$2" \
    '.grants[]? | select(.type == "catalog" and .privilege == $privilege)' \
    >/dev/null; then
    return
  fi
  put "$url" "$(jq -nc --arg privilege "$2" \
    '{grant:{type:"catalog",privilege:$privilege}}')" >/dev/null
}

grant catalog_contributor CATALOG_MANAGE_ACCESS
grant catalog_contributor CATALOG_MANAGE_METADATA
grant catalog_contributor CATALOG_MANAGE_CONTENT
grant catalog_reader TABLE_READ_DATA
grant catalog_reader TABLE_READ_PROPERTIES
grant catalog_reader CATALOG_READ_PROPERTIES

assign_principal_role() {
  url="$API/principals/$1/principal-roles"
  if get "$url" | jq -e --arg name "$2" \
    '.roles[]? | select(.name == $name)' >/dev/null; then
    return
  fi
  put "$url" "$(jq -nc --arg name "$2" \
    '{principalRole:{name:$name}}')" >/dev/null
}

assign_catalog_role() {
  url="$API/principal-roles/$1/catalog-roles/$POLARIS_CATALOG"
  if get "$url" | jq -e --arg name "$2" \
    '.roles[]? | select(.name == $name)' >/dev/null; then
    return
  fi
  put "$url" "$(jq -nc --arg name "$2" \
    '{catalogRole:{name:$name}}')" >/dev/null
}

assign_principal_role dev data_engineer
assign_principal_role analyst data_analyst
assign_catalog_role data_engineer catalog_contributor
assign_catalog_role data_analyst catalog_reader

echo "Polaris catalog $POLARIS_CATALOG is ready"
