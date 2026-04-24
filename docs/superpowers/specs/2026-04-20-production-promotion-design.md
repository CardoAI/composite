# Production Promotion Composite Actions — Design Spec

## Overview

Two composite actions to support CalVer-based production promotion via GitHub Releases. Part of the git flow described in the team's Git Flow documentation (April 2026).

**Context:** Service repos use thin wrapper workflows that call reusable workflows from `CardoAI/reusable-workflows`, which in turn use composite actions from this repo (`CardoAI/ci-cd/composite`). Production deployments are triggered by `release: [published]` events.

## Actions

### 1. `validate-release`

**Purpose:** Gate production deployments. Runs first in the release workflow and fails fast on invalid releases.

**Inputs:**

| Input | Required | Default | Description |
|---|---|---|---|
| `tag` | no | `${{ github.ref_name }}` | Release tag name (e.g., `v2026.3.0`) |

Branch information comes from `github.event.release.target_commitish`. Ancestry check uses git history (requires `fetch-depth: 0` in checkout).

**Outputs:**

| Output | Description |
|---|---|
| `version` | Validated tag without `v` prefix (e.g., `2026.3.1`) |
| `year` | Year component (e.g., `2026`) |
| `minor` | Minor component (e.g., `3`) |
| `patch` | Patch component (e.g., `1`) |
| `is-hotfix` | `true` if released from a `hotfix/*` branch, `false` otherwise |

**Validation steps (executed in order, fail-fast):**

1. **CalVer format** — Tag must match `^v[0-9]{4}\.[0-9]+\.[0-9]+$`. Rejects malformed tags like `v2026.3`, `2026.3.0` (missing `v`), `v2026.03.0` (leading zeros are allowed by regex but semantically fine).
2. **Year check** — Year component must be `>=` current calendar year. Rejects past-year tags (e.g., `v2025.1.0` created in 2026). Does NOT reject future years (edge case: year rollover during release).
3. **Branch check** — `target_commitish` must be `main` or match `hotfix/*`. Rejects releases from `dev`, feature branches, or arbitrary SHAs.
4. **Hotfix-patch coherence** — If target is `main`, patch must be `0` (feature release). If target is `hotfix/*`, patch must be `> 0` (hotfix release). Enforces the CalVer convention from the git flow doc.
5. **Rollback protection** — The tagged commit (`$GITHUB_SHA`) must be a descendant of the latest existing `v*` tag. Uses `git merge-base --is-ancestor`. Skipped if no prior `v*` tags exist (first release).

Each validation failure produces a clear error message and exits with code 1.

### 2. `update-production-tag`

**Purpose:** After a successful production deployment, force-update the floating `production` tag to the deployed commit.

**Inputs:**

| Input | Required | Description |
|---|---|---|
| `token` | yes | GitHub token with push permissions for force-pushing the tag |

**Steps:**

1. Configure git with the token for authentication.
2. Force-create `production` tag at `${{ github.sha }}`.
3. Force-push `production` tag to origin.

## Design Decisions

### Separation of concerns
Validation and tag update are separate actions because:
- Validation runs **before** deployment and should fail fast.
- Production tag update runs **after** successful deployment.
- Calling workflow controls orchestration: validate -> deploy -> update-production-tag.
- Matches existing repo pattern of single-purpose composite actions.

### No Docker image handling
Image retag/build is handled by existing composite actions (`copy-ecr-image-v2`, `single-platform-docker-build-v5`). This action does not duplicate that responsibility.

### CalVer validation level
Format + partial sequence validation (option C). Validates format and rejects past-year tags, but does not enforce strict sequential incrementing. Rationale: strict sequencing is brittle with failed releases, deleted tags, and parallel hotfixes.

### Hotfix-patch coherence enforcement
Feature releases from `main` must have patch `0`. Hotfix releases from `hotfix/*` must have patch `> 0`. This enforces the versioning convention and catches accidental misuse.

## Usage Example (in calling workflow — not our deliverable)

```yaml
on:
  release:
    types: [published]

jobs:
  deploy-production:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd #v6.0.2
        with:
          fetch-depth: 0  # required for rollback protection ancestry check

      - name: Validate release
        uses: CardoAI/ci-cd/composite/validate-release@main
        id: validate

      # Image retag (feature release) or build (hotfix) using existing actions
      # Deploy using existing actions (update-image-digest, etc.)

      - name: Update production tag
        uses: CardoAI/ci-cd/composite/update-production-tag@main
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```

## Error Messages

| Validation | Error |
|---|---|
| Format | `ERROR: Tag 'xyz' does not match CalVer format v<YEAR>.<MINOR>.<PATCH>` |
| Year | `ERROR: Tag year 2025 is in the past (current year: 2026)` |
| Branch | `ERROR: Releases must target 'main' or 'hotfix/*' branches, got 'dev'` |
| Coherence (main) | `ERROR: Feature releases from 'main' must have patch version 0, got 3` |
| Coherence (hotfix) | `ERROR: Hotfix releases must have patch version > 0, got 0` |
| Rollback | `ERROR: Tag v2026.3.0 is based on a commit older than v2026.4.0. Releases must not roll back production.` |
