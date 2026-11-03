# Scan frontend

Scans the checked-out frontend with Trivy before build or deployment. Includes
production and development dependencies from the lockfile, plus secrets in source
files. Dependencies are not installed and application scripts are not executed.
This is dependency and secret scanning, not application-code SAST or an IaC scan.

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
(`--severity CRITICAL --ignore-unfixed --exit-code 1`). Lower severities, unfixed
vulnerabilities, and secrets are reported without blocking. Missing manifests or
lockfiles, scanner errors, and database download failures also fail the action.
Repository-owned Trivy configuration and ignore files follow Trivy's normal
behavior; review changes to them as security policy changes.

Each invocation uploads a uniquely named `frontend-scan-*` artifact containing
`trivy.json`, including findings of every severity, unfixed vulnerabilities, and
secrets. Reports remain available when the gate fails and expire after seven days.
Treat them as sensitive: secret findings can include source snippets. Logs show
the report summary and the blocking vulnerabilities, without listing secrets.

Run this action once in a separate job with `contents: read`, no deployment
credentials, and no inherited secrets. Require it through `needs` on every build
or deployment job. It needs Bash and outbound access to GitHub releases and the
Trivy database registries, and works without Docker. The scanner version and
upstream actions are pinned; the database cache is refreshed through Trivy's
normal update checks.

Run the local contract checks with `python3 -m unittest discover -s scan-frontend`.
