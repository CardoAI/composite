#!/usr/bin/env bash
# Runs the whole scan_image_v7 action locally (FCS scan + report + fixable-criticals check),
# then fetches the stored report from CrowdStrike for the same image (fetch-report.sh) to compare.
#
# Usage: FALCON_CLIENT_ID=... FALCON_CLIENT_SECRET=... ./scan-and-fetch.sh <image:tag>
#
# Output: scan-results.json next to this script (same file as fetch-report.sh). It first holds the JSON written by
# the FCS CLI during the scan (what the action checks in CI), then is overwritten by the report fetched from CrowdStrike.
#
# Optional env overrides (same meaning as the action.yaml inputs):
#   FALCON_REGION (default: eu-1), SOCKET, MINIMUM_SCORE, MINIMUM_SEVERITY, MINIMUM_EXPRT,
#   EXCLUDE_VULNERABILITIES, VULN_FIXABLE_ONLY, MINIMUM_DETECTION_SEVERITY, TIMEOUT, FAIL_ON,
#   UPLOAD_RESULTS (default: true, like action.yaml), FCS_VERSION
#   FCS_BIN: path to a local fcs binary; skips the CLI download
#   ECR_AWS_PROFILE: AWS profile used to log in to ECR for ECR images (default: cardoai-eu-artifact-repository)
#   FETCH_DELAY: seconds to wait between the scan and the fetch (default: 0)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${1:-}"
RESULTS_PATH="$SCRIPT_DIR/scan-results.json"
ECR_AWS_PROFILE="${ECR_AWS_PROFILE:-cardoai-eu-artifact-repository}"
export FALCON_REGION="${FALCON_REGION:-eu-1}"

if [[ -z "$IMAGE" ]]; then
  echo "Usage: $0 <image:tag>"
  exit 1
fi
if [[ -z "${FALCON_CLIENT_ID:-}" || -z "${FALCON_CLIENT_SECRET:-}" ]]; then
  echo "❌ Error: FALCON_CLIENT_ID and FALCON_CLIENT_SECRET must be set."
  exit 1
fi

# Use the same fcs-action commit as action.yaml
FCS_ACTION_REF="$(grep -oE 'crowdstrike/fcs-action@[0-9a-f]{40}' "$SCRIPT_DIR/action.yaml" | head -1 | cut -d@ -f2)"
if [[ -z "$FCS_ACTION_REF" ]]; then
  echo "❌ Error: Could not find the crowdstrike/fcs-action commit in action.yaml."
  exit 1
fi

# --- 1. ECR login and image pull ---
if [[ "$IMAGE" =~ ^([0-9]{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/ ]]; then
  ECR_REGISTRY="${BASH_REMATCH[1]}.dkr.ecr.${BASH_REMATCH[2]}.amazonaws.com"
  echo "=== Logging in to ECR $ECR_REGISTRY (profile: $ECR_AWS_PROFILE) ==="
  aws ecr get-login-password --region "${BASH_REMATCH[2]}" --profile "$ECR_AWS_PROFILE" \
    | docker login --username AWS --password-stdin "$ECR_REGISTRY" || {
    echo "❌ Error: ECR login failed. Check the AWS profile '$ECR_AWS_PROFILE' (e.g. run 'aws sso login --profile $ECR_AWS_PROFILE')."
    exit 1
  }
fi

echo "=== Pulling $IMAGE ==="
docker pull "$IMAGE" || {
  echo "❌ Error: Failed to pull '$IMAGE'."
  exit 1
}

# --- 2. FCS scan with the fcs-action scripts ---
# Keep temp files under $HOME (in a non-hidden dir): snap-installed docker has a private /tmp,
# so image exports written there by the FCS CLI are invisible to it and the scan fails with "Failed to pull image"
WORK_DIR="$(mktemp -d -p "$HOME" fcs-scan.XXXXXX)"
mkdir -p "$WORK_DIR/tmp"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "=== Fetching crowdstrike/fcs-action@$FCS_ACTION_REF ==="
ACTION_DIR="$WORK_DIR/fcs-action"
git init -q "$ACTION_DIR"
git -C "$ACTION_DIR" fetch -q --depth 1 https://github.com/crowdstrike/fcs-action.git "$FCS_ACTION_REF" || exit 1
git -C "$ACTION_DIR" checkout -q FETCH_HEAD || exit 1

# Emulate the GitHub Actions runner environment expected by the action scripts
export GITHUB_ACTION_PATH="$ACTION_DIR"
export GITHUB_WORKSPACE="$PWD"
export GITHUB_OUTPUT="$WORK_DIR/github_output"
export RUNNER_TEMP="$WORK_DIR"
unset GITHUB_STEP_SUMMARY GITHUB_PATH
touch "$GITHUB_OUTPUT"

export FALCON_CLIENT_SECRET
export INPUT_FALCON_CLIENT_ID="$FALCON_CLIENT_ID"
export INPUT_FALCON_REGION="$FALCON_REGION"

if [[ -n "${FCS_BIN:-}" ]]; then
  echo "=== Using local FCS CLI: $FCS_BIN ==="
  OUTPUT_FCS_BIN="$(command -v "$FCS_BIN")"
else
  echo "=== Downloading FCS CLI ==="
  INPUT_BIN_PATH="$WORK_DIR" INPUT_VERSION="${FCS_VERSION:-}" "$ACTION_DIR/fcs_download.sh" || {
    echo "❌ Error: FCS CLI download failed. The API client may lack the scope to download the CLI."
    echo "   Set FCS_BIN to a local fcs binary to skip the download (e.g. FCS_BIN=/usr/local/bin/fcs)."
    exit 1
  }
  OUTPUT_FCS_BIN="$(grep '^FCS_BIN=' "$GITHUB_OUTPUT" | tail -1 | cut -d= -f2-)"
fi
if [[ -z "$OUTPUT_FCS_BIN" ]]; then
  echo "❌ Error: FCS CLI binary not found."
  exit 1
fi
export OUTPUT_FCS_BIN

echo "=== Running FCS image scan on $IMAGE ==="
rm -f "$RESULTS_PATH"
# Same inputs and defaults as action.yaml
INPUT_SCAN_TYPE="image" \
INPUT_IMAGE="$IMAGE" \
INPUT_SOCKET="${SOCKET:-unix:///var/run/docker.sock}" \
INPUT_MINIMUM_SCORE="${MINIMUM_SCORE:-}" \
INPUT_MINIMUM_SEVERITY="${MINIMUM_SEVERITY:-}" \
INPUT_MINIMUM_EXPRT="${MINIMUM_EXPRT:-}" \
INPUT_EXCLUDE_VULNERABILITIES="${EXCLUDE_VULNERABILITIES:-}" \
INPUT_VULN_FIXABLE_ONLY="${VULN_FIXABLE_ONLY:-false}" \
INPUT_MINIMUM_DETECTION_SEVERITY="${MINIMUM_DETECTION_SEVERITY:-}" \
INPUT_SHOW_FULL_DESCRIPTION="true" \
INPUT_SHOW_FULL_DETECTION_DETAILS="true" \
INPUT_TIMEOUT="${TIMEOUT:-300}" \
INPUT_FAIL_ON="${FAIL_ON:-critical=1,high=1}" \
INPUT_UPLOAD_RESULTS="${UPLOAD_RESULTS:-true}" \
INPUT_OUTPUT_PATH="$RESULTS_PATH" \
INPUT_TEMP_DIR="$WORK_DIR/tmp" \
TMPDIR="$WORK_DIR/tmp" \
"$ACTION_DIR/fcs-scan.sh"
SCAN_EXIT_CODE=$?
# fcs-scan.sh reports the FCS CLI exit code through GITHUB_OUTPUT rather than its own exit status
CLI_EXIT_CODE="$(grep '^exit-code=' "$GITHUB_OUTPUT" | tail -1 | cut -d= -f2-)"
SCAN_EXIT_CODE="${CLI_EXIT_CODE:-$SCAN_EXIT_CODE}"

echo
if [[ ! -f "$RESULTS_PATH" ]]; then
  echo "❌ Error: Scan did not produce '$RESULTS_PATH' (exit code $SCAN_EXIT_CODE)."
  exit 1
fi
echo "✅ Scan results saved to $RESULTS_PATH (scan exit code $SCAN_EXIT_CODE)"

# Prints the ExPRT rating counts of a report
print_exprt_coverage() {
  python3 - "$1" <<'EOF'
import json, sys
from collections import Counter

vulnerabilities = json.load(open(sys.argv[1])).get("Vulnerabilities") or []
ratings = Counter(
    (((((item or {}).get("Vulnerability") or {}).get("Details") or {}).get("cps_rating") or {}).get("CurrentRating") or {}).get("Rating")
    or "N/A"
    for item in vulnerabilities
)
print(f"{len(vulnerabilities)} vulnerabilities, ExPRT ratings: {dict(ratings.most_common())}")
EOF
}

# --- 3. Report and fixable-criticals check on the scan output (same steps as action.yaml) ---
echo
echo "=== Generate Report Summary (scan output) ==="
python3 "$SCRIPT_DIR/generate-report.py" "$RESULTS_PATH"

echo
echo "=== Check Fixable Critical Vulnerabilities (scan output) ==="
python3 "$SCRIPT_DIR/check-fixable-criticals.py" "$RESULTS_PATH"
ACTION_EXIT_CODE=$?
# Computed now because the fetch below overwrites the file
SCAN_COVERAGE="$(print_exprt_coverage "$RESULTS_PATH")"

# --- 4. Fetch the stored report from CrowdStrike (overwrites scan-results.json) and check it too ---
if [[ "${FETCH_DELAY:-0}" -gt 0 ]]; then
  echo
  echo "=== Waiting ${FETCH_DELAY}s before fetching the report ==="
  sleep "$FETCH_DELAY"
fi
echo
echo "=== Fetch report from CrowdStrike ==="
SCAN_OUTPUT_MTIME="$(stat -c %Y "$RESULTS_PATH")"
sleep 1 # makes sure a fetched file gets a different mtime
OUTPUT_PATH="$RESULTS_PATH" "$SCRIPT_DIR/fetch-report.sh" "$IMAGE"
FETCH_EXIT_CODE=$?

# --- 5. ExPRT coverage of both reports ---
echo
echo "=== ExPRT rating coverage ==="
echo "Scan output:    $SCAN_COVERAGE"
# fetch-report.sh only replaces the file when the download succeeds
if [[ "$(stat -c %Y "$RESULTS_PATH")" != "$SCAN_OUTPUT_MTIME" ]]; then
  echo "Fetched report: $(print_exprt_coverage "$RESULTS_PATH")"
else
  echo "Fetched report: not downloaded, $RESULTS_PATH still holds the scan output"
fi

echo
echo "Action check exit code: $ACTION_EXIT_CODE (scan output), fetch-report exit code: $FETCH_EXIT_CODE"
exit "$ACTION_EXIT_CODE"
