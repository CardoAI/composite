#!/usr/bin/env bash
set -euo pipefail

: "${WORKING_DIRECTORY:=.}"
: "${REPORT_DIRECTORY:?Report directory is required}"
case "${SCAN_MODE:-normal}" in
    normal) gate_exit_code=1 ;;
    report-only) gate_exit_code=0 ;;
    *)
        echo "::error::Frontend scan mode must be normal or report-only."
        exit 1
        ;;
esac
cd -- "$WORKING_DIRECTORY"

if [[ ! -f package.json ]]; then
    echo "::error::Frontend scan requires package.json in the working directory."
    exit 1
fi

expected_lockfile=""
# Match Yarn builds first, then npm's shrinkwrap precedence over package-lock.json.
for lockfile in yarn.lock npm-shrinkwrap.json package-lock.json pnpm-lock.yaml bun.lock; do
    if [[ -f "$lockfile" ]]; then
        expected_lockfile="$lockfile"
        break
    fi
done
if [[ -z "$expected_lockfile" ]]; then
    echo "::error::Frontend scan requires yarn.lock, package-lock.json, pnpm-lock.yaml, or bun.lock."
    exit 1
fi

# Keep all dependency findings in the report, including unfixed issues.
trivy fs \
    --scanners vuln \
    --include-dev-deps \
    --skip-db-update=false \
    --list-all-pkgs \
    --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
    --ignore-unfixed=false \
    --exit-code 0 \
    --format json \
    --output "$REPORT_DIRECTORY/trivy.json" \
    --timeout 10m \
    --no-progress \
    .

EXPECTED_LOCKFILE="$expected_lockfile" trivy convert \
    --format template \
    --template "@${GITHUB_ACTION_PATH}/check-coverage.tpl" \
    --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
    --ignorefile '' --exit-code 0 --output '' \
    "$REPORT_DIRECTORY/trivy.json"
touch "$REPORT_DIRECTORY/coverage-ok"

# Keep all dependency findings visible in the workflow logs.
trivy convert --format table --exit-code 0 --output '' "$REPORT_DIRECTORY/trivy.json"

# Reuse the same database; the mode only changes whether findings block the build.
trivy fs \
    --scanners vuln \
    --include-dev-deps \
    --skip-db-update \
    --severity CRITICAL \
    --ignore-unfixed \
    --exit-code "$gate_exit_code" \
    --format table \
    --output '' \
    --timeout 10m \
    --no-progress \
    .
