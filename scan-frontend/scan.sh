#!/usr/bin/env bash
set -euo pipefail

: "${WORKING_DIRECTORY:=.}"
: "${REPORT_DIRECTORY:?Report directory is required}"
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
    --list-all-pkgs \
    --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
    --ignore-unfixed=false \
    --exit-code 0 \
    --format json \
    --output "$REPORT_DIRECTORY/trivy.json" \
    --timeout 10m \
    --no-progress \
    .

# A completed first scan has prepared the database, even if the gate later fails.
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    echo "database-ready=true" >> "$GITHUB_OUTPUT"
fi

EXPECTED_LOCKFILE="$expected_lockfile" trivy convert \
    --format template \
    --template "@${GITHUB_ACTION_PATH}/check-coverage.tpl" \
    --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
    --ignorefile '' --exit-code 0 --output '' \
    "$REPORT_DIRECTORY/trivy.json"
touch "$REPORT_DIRECTORY/coverage-ok"

# Keep all dependency findings visible in the workflow logs.
trivy convert --format table --exit-code 0 --output '' "$REPORT_DIRECTORY/trivy.json"

# Only fixable critical CVEs block deployment.
trivy fs \
    --scanners vuln \
    --include-dev-deps \
    --severity CRITICAL \
    --ignore-unfixed \
    --exit-code 1 \
    --format table \
    --output '' \
    --timeout 10m \
    --no-progress \
    .
