#!/usr/bin/env bash
# Downloads the image assessment report of an already scanned image from CrowdStrike (no local scan).
# The report is the one uploaded by the scan in CI (upload_results: true) and has the same JSON format
# as the FCS CLI output, so it can be passed to run-local.sh (or generate-report.py / check-fixable-criticals.py).
#
# Usage: FALCON_CLIENT_ID=... FALCON_CLIENT_SECRET=... ./fetch-report.sh <image:tag> [output.json]
# Default output: scan-results.json next to this script (the file run-local.sh reads by default)
#
# Optional env overrides:
#   FALCON_REGION: us-1, us-2 or eu-1 (default: eu-1)
#   REPOSITORY / TAG: override the repository and tag parsed from the image reference
set -uo pipefail

IMAGE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_PATH="${2:-$SCRIPT_DIR/scan-results.json}"
FALCON_REGION="${FALCON_REGION:-eu-1}"

if [[ -z "$IMAGE" ]]; then
  echo "Usage: $0 <image:tag> [output.json]"
  exit 1
fi
if [[ -z "${FALCON_CLIENT_ID:-}" || -z "${FALCON_CLIENT_SECRET:-}" ]]; then
  echo "❌ Error: FALCON_CLIENT_ID and FALCON_CLIENT_SECRET must be set."
  exit 1
fi

case "$FALCON_REGION" in
  us-1) API_HOST="api.crowdstrike.com" ;;
  us-2 | eu-1) API_HOST="api.$FALCON_REGION.crowdstrike.com" ;;
  *)
    echo "❌ Error: Unsupported FALCON_REGION '$FALCON_REGION'. Use us-1, us-2 or eu-1."
    exit 1
    ;;
esac
REPORT_HOST="container-upload.$FALCON_REGION.crowdstrike.com"

# Split "registry/repo:tag" into repository and tag (the last ':' after the last '/' is the tag separator)
if [[ "${IMAGE##*/}" == *:* ]]; then
  DEFAULT_REPOSITORY="${IMAGE%:*}"
  DEFAULT_TAG="${IMAGE##*:}"
else
  DEFAULT_REPOSITORY="$IMAGE"
  DEFAULT_TAG="latest"
fi
# CrowdStrike stores the repository without the registry host, and single-name repositories
# under "library/" (Docker Hub convention), e.g. "<id>.dkr.ecr.<region>.amazonaws.com/app" -> "library/app"
FIRST_COMPONENT="${DEFAULT_REPOSITORY%%/*}"
if [[ "$DEFAULT_REPOSITORY" == */* && ( "$FIRST_COMPONENT" == *.* || "$FIRST_COMPONENT" == *:* || "$FIRST_COMPONENT" == "localhost" ) ]]; then
  DEFAULT_REPOSITORY="${DEFAULT_REPOSITORY#*/}"
fi
[[ "$DEFAULT_REPOSITORY" != */* ]] && DEFAULT_REPOSITORY="library/$DEFAULT_REPOSITORY"
REPOSITORY="${REPOSITORY:-$DEFAULT_REPOSITORY}"
TAG="${TAG:-$DEFAULT_TAG}"

echo "=== Authenticating to $API_HOST ==="
# Credentials are sent through stdin so they don't show up in the process list
TOKEN_RESPONSE="$(printf 'client_id=%s&client_secret=%s' "$FALCON_CLIENT_ID" "$FALCON_CLIENT_SECRET" \
  | curl -sS -X POST "https://$API_HOST/oauth2/token" \
    -H "Content-Type: application/x-www-form-urlencoded" --data @-)" || exit 1
ACCESS_TOKEN="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token") or "")' <<<"$TOKEN_RESPONSE" 2>/dev/null)"
if [[ -z "$ACCESS_TOKEN" ]]; then
  echo "❌ Error: Failed to get an access token. Response:"
  echo "$TOKEN_RESPONSE"
  exit 1
fi

echo "=== Fetching report for repository '$REPOSITORY', tag '$TAG' ==="
mkdir -p "$(dirname "$OUTPUT_PATH")"
TMP_OUTPUT="$(mktemp)"
trap 'rm -f "$TMP_OUTPUT"' EXIT

HTTP_CODE="$(curl -sS -G "https://$REPORT_HOST/reports" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "repository=$REPOSITORY" \
  --data-urlencode "tag=$TAG" \
  -o "$TMP_OUTPUT" -w '%{http_code}')" || exit 1

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "❌ Error: Report request failed with HTTP $HTTP_CODE. Response:"
  cat "$TMP_OUTPUT"
  echo
  [[ "$HTTP_CODE" == "403" ]] && echo "   The API client may lack the 'Falcon Container Image: Read' scope."
  [[ "$HTTP_CODE" == "404" ]] && echo "   No report found: check the image was scanned with upload_results and the repository/tag match."
  exit 1
fi

if ! python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if "Vulnerabilities" in d else 1)' "$TMP_OUTPUT" 2>/dev/null; then
  echo "❌ Error: Response is not an image assessment report. Response:"
  head -c 2000 "$TMP_OUTPUT"
  echo
  exit 1
fi

mv "$TMP_OUTPUT" "$OUTPUT_PATH"
echo "✅ Report saved to $OUTPUT_PATH"
echo "Next: $SCRIPT_DIR/run-local.sh $OUTPUT_PATH"
