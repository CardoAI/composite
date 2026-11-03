# Scan frontend

Scans frontend dependencies with Trivy before build or deployment. Includes
production and development dependencies from dependency manifests and lockfiles.
Dependencies are not installed and application scripts are not executed.
Both scans explicitly select only `--scanners vuln`; secret scanning is disabled.
This is dependency vulnerability scanning, not application-code SAST or an IaC scan.
Trivy still reads dependency metadata, so keep credential values out of manifests
and lockfiles. This configuration does not sandbox the scanner from credentials
already present on the runner.

```yaml
jobs:
  security-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: CardoAI/composite/scan-frontend@main
        # with:
        #   working-directory: frontend

  build:
    needs: security-scan
    # Existing build and deployment steps.
```

The working directory defaults to `.` and must contain `package.json` and a
supported lockfile: `yarn.lock`, `package-lock.json`, `npm-shrinkwrap.json`,
`pnpm-lock.yaml`, or `bun.lock`. Use the workspace root for monorepos so the shared
lockfile and workspace manifests are scanned together. Commit an up-to-date
lockfile; `package.json` alone cannot provide resolved dependency versions.

The gate fails on **CRITICAL dependency vulnerabilities with an available fix**
(`--severity CRITICAL --ignore-unfixed --exit-code 1`). Lower severities and unfixed
vulnerabilities are reported without blocking. Missing manifests or
lockfiles, scanner errors, and database download failures also fail the action.
Repository-owned Trivy configuration and ignore files follow Trivy's normal
behavior; review changes to them as security policy changes.

The workflow run's GitHub job summary shows the scan outcome, severity counts,
fixable critical count, and dependency vulnerability details. The summary is also
published after scan failures; missing or invalid reports are marked incomplete. Details are limited
to 100 findings, ordered by severity, with long fields shortened. Workflow logs
contain all dependency findings, including lower severities and unfixed issues.
No scan artifact is uploaded: the temporary JSON report is used to render the
logs and summary, then removed even when the gate fails.
This uses `GITHUB_STEP_SUMMARY`, like the
CrowdStrike action, and needs no extra token permissions or PR comments.

Run this action once in a separate job with `contents: read`, no deployment
credentials, and no inherited secrets. Require it through `needs` on every build
or deployment job. It needs Bash and outbound access to GitHub releases and the
Trivy database registries, and works without Docker. The scanner version and
upstream actions are pinned; the database cache is refreshed through Trivy's
normal update checks.

Run the local contract checks with `python3 -m unittest discover -s scan-frontend`.
Summary rendering tests also run when `trivy` is on `PATH`, or when `TRIVY_BIN`
points to a Trivy binary.
