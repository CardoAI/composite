#!/usr/bin/env bash
# Downloads the CrowdStrike image assessment report of an already scanned image (no local scan), then runs
# the report generation and the fixable-criticals check against it.
# The report is the one uploaded by the scan in CI (upload_results: true) and has the same JSON format as the FCS CLI output.
#
# Usage:
#   FALCON_CLIENT_ID=... FALCON_CLIENT_SECRET=... ./run-local.sh <image:tag>   # fetch the report, then check it
#   ./run-local.sh [path/to/scan-results.json]                                   # check an existing report only
#
# The fetched report is saved as scan-results.json next to this script (override with OUTPUT_PATH).
#
# Optional env overrides:
#   FALCON_REGION: us-1, us-2 or eu-1 (default: eu-1)
#   REPOSITORY / TAG: override the repository and tag parsed from the image reference
#   OUTPUT_PATH: where to save the fetched report
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$SCRIPT_DIR/scan-results.json}"

fetch_report() {
  local image="$1" output_path="$2"
  local falcon_region="${FALCON_REGION:-eu-1}" api_host report_host

  if [[ -z "${FALCON_CLIENT_ID:-}" || -z "${FALCON_CLIENT_SECRET:-}" ]]; then
    echo "❌ Error: FALCON_CLIENT_ID and FALCON_CLIENT_SECRET must be set to fetch a report."
    return 1
  fi

  case "$falcon_region" in
    us-1) api_host="api.crowdstrike.com" ;;
    us-2 | eu-1) api_host="api.$falcon_region.crowdstrike.com" ;;
    *)
      echo "❌ Error: Unsupported FALCON_REGION '$falcon_region'. Use us-1, us-2 or eu-1."
      return 1
      ;;
  esac
  report_host="container-upload.$falcon_region.crowdstrike.com"

  # Split "registry/repo:tag" into repository and tag (the last ':' after the last '/' is the tag separator)
  local repository tag first_component
  if [[ "${image##*/}" == *:* ]]; then
    repository="${image%:*}"
    tag="${image##*:}"
  else
    repository="$image"
    tag="latest"
  fi
  # CrowdStrike stores the repository without the registry host, and single-name repositories
  # under "library/" (Docker Hub convention), e.g. "<id>.dkr.ecr.<region>.amazonaws.com/app" -> "library/app"
  first_component="${repository%%/*}"
  if [[ "$repository" == */* && ( "$first_component" == *.* || "$first_component" == *:* || "$first_component" == "localhost" ) ]]; then
    repository="${repository#*/}"
  fi
  [[ "$repository" != */* ]] && repository="library/$repository"
  repository="${REPOSITORY:-$repository}"
  tag="${TAG:-$tag}"

  echo "=== Authenticating to $api_host ==="
  # Credentials are sent through stdin so they don't show up in the process list
  local token_response access_token
  token_response="$(printf 'client_id=%s&client_secret=%s' "$FALCON_CLIENT_ID" "$FALCON_CLIENT_SECRET" \
    | curl -sS -X POST "https://$api_host/oauth2/token" \
      -H "Content-Type: application/x-www-form-urlencoded" --data @-)" || return 1
  access_token="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token") or "")' <<<"$token_response" 2>/dev/null)"
  if [[ -z "$access_token" ]]; then
    echo "❌ Error: Failed to get an access token. Response:"
    echo "$token_response"
    return 1
  fi

  echo "=== Fetching report for repository '$repository', tag '$tag' ==="
  mkdir -p "$(dirname "$output_path")"
  TMP_OUTPUT="$(mktemp)"
  trap 'rm -f "$TMP_OUTPUT"' EXIT

  local http_code
  http_code="$(curl -sS -G "https://$report_host/reports" \
    -H "Authorization: Bearer $access_token" \
    --data-urlencode "repository=$repository" \
    --data-urlencode "tag=$tag" \
    -o "$TMP_OUTPUT" -w '%{http_code}')" || return 1

  if [[ "$http_code" != "200" ]]; then
    echo "❌ Error: Report request failed with HTTP $http_code. Response:"
    cat "$TMP_OUTPUT"
    echo
    [[ "$http_code" == "403" ]] && echo "   The API client may lack the 'Falcon Container Image: Read' scope."
    [[ "$http_code" == "404" ]] && echo "   No report found: check the image was scanned with upload_results and the repository/tag match."
    return 1
  fi

  if ! python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if "Vulnerabilities" in d else 1)' "$TMP_OUTPUT" 2>/dev/null; then
    echo "❌ Error: Response is not an image assessment report. Response:"
    head -c 2000 "$TMP_OUTPUT"
    echo
    return 1
  fi

  mv "$TMP_OUTPUT" "$output_path"
  echo "✅ Report saved to $output_path"
  echo
}

# An existing .json file is checked as is; anything else is treated as an image reference to fetch
if [[ "$TARGET" == *.json ]]; then
  RESULTS_FILE="$TARGET"
else
  RESULTS_FILE="${OUTPUT_PATH:-$SCRIPT_DIR/scan-results.json}"
  fetch_report "$TARGET" "$RESULTS_FILE" || exit 1
fi

if [[ ! -f "$RESULTS_FILE" ]]; then
  echo "❌ Error: The file '$RESULTS_FILE' was not found."
  echo "Usage: $0 <image:tag> | [path/to/scan-results.json]"
  exit 1
fi

# Make sure the report is printed to the console instead of a GitHub Job Summary
unset GITHUB_STEP_SUMMARY

echo "=== Generate Report Summary ==="
python3 "$SCRIPT_DIR/generate-report.py" "$RESULTS_FILE"

echo
echo "=== Check Fixable Critical Vulnerabilities ==="
python3 "$SCRIPT_DIR/check-fixable-criticals.py" "$RESULTS_FILE"
EXIT_CODE=$?

echo
echo "Exit code: $EXIT_CODE"
exit "$EXIT_CODE"
