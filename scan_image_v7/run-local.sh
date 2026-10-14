#!/usr/bin/env bash
# Runs the report generation and the fixable-criticals check against a local scan results file.
# Usage: ./run-local.sh [path/to/scan-results.json]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_FILE="${1:-$SCRIPT_DIR/scan-results.json}"

if [[ ! -f "$RESULTS_FILE" ]]; then
  echo "❌ Error: The file '$RESULTS_FILE' was not found."
  echo "Usage: $0 [path/to/scan-results.json]"
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
