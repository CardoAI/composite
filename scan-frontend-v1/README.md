# Scan frontend v1

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
      - uses: CardoAI/composite/scan-frontend-v1@main
        with:
          mode: normal
          # working-directory: frontend

  build:
    needs: security-scan
    # Existing build and deployment steps.
```

The working directory defaults to `.` and must contain `package.json` and a
supported lockfile: `yarn.lock`, `package-lock.json`, `pnpm-lock.yaml`, or `bun.lock`.
Use the workspace root for monorepos so the shared
lockfile and workspace manifests are scanned together. Commit an up-to-date
lockfile; `package.json` alone cannot provide resolved dependency versions.
Coverage must include resolved packages from the selected root lockfile, even
when no vulnerabilities are found. Selection prefers `yarn.lock`, matching the
frontend build actions. npm shrinkwrap takes precedence over `package-lock.json`,
followed by `pnpm-lock.yaml` and `bun.lock`. Trivy v0.76.1 does not analyze
`npm-shrinkwrap.json`; those projects fail as incomplete rather than falling back
to a different lockfile. Other lockfiles cannot substitute for a skipped
or unparseable selected lockfile. Projects without an analyzable package inventory
fail as incomplete.

The `mode` input accepts `normal` (default) or `report-only`:

| Mode | Vulnerability findings | Scanner errors or incomplete coverage |
| --- | --- | --- |
| `normal` | Fixable CRITICAL findings fail the action. | Fail the action. |
| `report-only` | Report findings without failing the vulnerability gate. | Fail the action. |

Invalid mode values fail before scanning. To start a non-enforcing rollout, set
`mode: report-only` on the action invocation; this does not use `continue-on-error`
or hide scanner failures.

In normal mode, the gate fails on **CRITICAL dependency vulnerabilities with an available fix**
(`--severity CRITICAL --ignore-unfixed --exit-code 1`). Lower severities and unfixed
vulnerabilities are reported without blocking. Missing manifests or
lockfiles, incomplete dependency coverage, scanner errors, and database download
failures also fail the action.
Repository-owned Trivy configuration and ignore files follow Trivy's normal
behavior; review changes to them as security policy changes. Output paths are
controlled by the action so repository output settings cannot overwrite scan
inputs or redirect the findings away from the logs.

The workflow run's GitHub job summary uses the CrowdStrike report's colored
severity icons, section headings, and bold totals. It shows the scan outcome,
severity counts, selected mode, fixable critical count, and dependency
vulnerability details. Status and severity labels remain readable alongside the
icons. In report-only mode it labels the scan as non-enforcing and identifies
findings that would block in normal mode. The summary is also
published after scan failures; missing or invalid reports are marked incomplete. Details are limited
to 100 findings, ordered by severity, with long fields shortened. The first 10 are
visible immediately; an expandable "Show more" section contains the remaining
summary rows. Workflow logs
contain all dependency findings, including lower severities and unfixed issues.
No scan artifact is uploaded: the temporary JSON report is used to render the
logs and summary, then removed even when the gate fails.
This uses `GITHUB_STEP_SUMMARY`, like the
CrowdStrike action, and needs no extra token permissions or PR comments.

Run this action once in a separate job with `contents: read`, no deployment
credentials, and no inherited secrets. Require it through `needs` on build jobs.
Run it only for the workflow's supported build branches; promotion jobs reuse the
build's security decision rather than rescanning tag source unrelated to the
copied assets. Establish artifact identity in the promotion process independently.
It needs Bash, curl, tar (or unzip for Windows), a SHA-256 tool, and outbound
access to GitHub releases and the Trivy database registries, and works without
Docker. Trivy is downloaded directly from GitHub Releases, following the
[setup-trivy workaround](https://github.com/aquasecurity/setup-trivy/issues/42),
with bounded retries and visible connection errors. Release archives are checked
against the committed `trivy-checksums.txt` before extraction, including on cache
hits. Update that file together with the version in `action.yaml` when upgrading
Trivy. Upstream actions are pinned. Only the release archive is cached across
runs, with a key scoped by version, OS, and architecture.
Every scan job uses a fresh database directory inside its unique temporary report
directory. The first pass explicitly enables database updates and downloads the
database; the gate pass disables database updates and reuses that same snapshot.
The database is deleted with the report after use, including on failure. Registry
or database download failures block the build. Freshness still depends on the
advisories included in Trivy's published database.

Run the local contract checks with `python3 -m unittest discover -s scan-frontend-v1`.
Coverage and summary rendering tests also run when `trivy` is on `PATH`, or when
`TRIVY_BIN` points to a Trivy binary.
