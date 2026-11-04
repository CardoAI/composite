#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_STEP_SUMMARY:?GitHub job summary file is required}"
scan_mode="${SCAN_MODE:-normal}"
case "$scan_mode" in
    normal|report-only) ;;
    *)
        printf '## 🛡️ Frontend dependency scan\n\n⚠️ **Scan incomplete:** mode must be normal or report-only.\n' >> "$GITHUB_STEP_SUMMARY"
        exit 1
        ;;
esac
summary_status=0
{
    printf '## 🛡️ Frontend dependency scan\n\n'
    printf '_Includes production and development dependencies. Secret scanning is disabled._\n\n'
    printf '**Mode: %s**\n\n' "$scan_mode"
    if [[ "$scan_mode" == 'report-only' ]]; then
        printf 'Vulnerability findings do not block deployment. Scanner errors and incomplete coverage still fail the job.\n\n'
    else
        printf 'Deployment policy: block CRITICAL dependency vulnerabilities with an available fix.\n\n'
    fi

    if [[ -n "${REPORT_DIRECTORY:-}" && -s "$REPORT_DIRECTORY/trivy.json" && -f "$REPORT_DIRECTORY/coverage-ok" ]]; then
        summary_fragment=$(mktemp "${REPORT_DIRECTORY}/summary.XXXXXX")
        if trivy convert --format template \
            --template "@${GITHUB_ACTION_PATH}/summary.tpl" \
            --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
            --ignorefile '' --exit-code 0 --output "$summary_fragment" \
            "$REPORT_DIRECTORY/trivy.json"; then
            case "${SCAN_OUTCOME:-skipped}" in
                success)
                    if [[ "$scan_mode" == 'report-only' ]]; then
                        printf 'ℹ️ **Report-only scan completed.** Findings are reported without enforcing the vulnerability gate.\n\n'
                    else
                        printf '✅ **Dependency gate passed.**\n\n'
                    fi
                    ;;
                failure) printf '❌ **Build and deployment blocked:** the scan did not pass. Review the findings and scan logs.\n\n' ;;
                *) printf '⚠️ **Scan incomplete:** the scan did not finish successfully. Review the scan logs.\n\n' ;;
            esac
            cat "$summary_fragment"
        else
            printf '⚠️ **Scan report unavailable:** the JSON report could not be rendered. Review the scan logs.\n'
            summary_status=1
        fi
        rm -f -- "$summary_fragment"
    else
        printf '⚠️ **Scan incomplete:** no complete dependency report with verified coverage was produced. Review the scan logs.\n'
        summary_status=1
    fi
} >> "$GITHUB_STEP_SUMMARY"
exit "$summary_status"
