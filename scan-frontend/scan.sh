#!/usr/bin/env bash
set -euo pipefail

: "${WORKING_DIRECTORY:=.}"
: "${REPORT_DIRECTORY:?Report directory is required}"
cd -- "$WORKING_DIRECTORY"

if [[ ! -f package.json ]]; then
    echo "::error::Frontend scan requires package.json in the working directory."
    exit 1
fi

if [[ ! -f yarn.lock && ! -f package-lock.json && ! -f npm-shrinkwrap.json && ! -f pnpm-lock.yaml && ! -f bun.lock ]]; then
    echo "::error::Frontend scan requires yarn.lock, package-lock.json, npm-shrinkwrap.json, pnpm-lock.yaml, or bun.lock."
    exit 1
fi

# Keep the complete report; filtering it here would hide secrets and unfixed issues.
trivy fs \
    --scanners vuln,secret \
    --include-dev-deps \
    --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
    --ignore-unfixed=false \
    --exit-code 0 \
    --format json \
    --output "$REPORT_DIRECTORY/trivy.json" \
    --timeout 10m \
    --no-progress \
    .

# Show counts without printing detected secret values to the workflow log.
trivy convert --format table --table-mode summary --exit-code 0 "$REPORT_DIRECTORY/trivy.json"

# Secret findings have no fixed version; only fixable critical CVEs block deployment.
trivy fs \
    --scanners vuln \
    --include-dev-deps \
    --severity CRITICAL \
    --ignore-unfixed \
    --exit-code 1 \
    --format table \
    --timeout 10m \
    --no-progress \
    .
