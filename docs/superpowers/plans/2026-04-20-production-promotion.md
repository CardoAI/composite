# Production Promotion Composite Actions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two composite actions (`validate-release` and `update-production-tag`) for CalVer-based production deployment gating.

**Architecture:** Two independent `action.yaml` files following existing repo conventions (kebab-case inputs, `$GITHUB_OUTPUT`, `shell: bash`, `set -e`). No external dependencies — pure bash validation logic.

**Tech Stack:** GitHub Actions composite actions, bash

**Spec:** `docs/superpowers/specs/2026-04-20-production-promotion-design.md`

---

## File Structure

| Action | File | Responsibility |
|---|---|---|
| validate-release | `validate-release/action.yaml` | CalVer format, year, branch, coherence, rollback checks |
| update-production-tag | `update-production-tag/action.yaml` | Force-update floating `production` tag |

---

### Task 1: Create `validate-release/action.yaml`

**Files:**
- Create: `validate-release/action.yaml`

- [ ] **Step 1: Create the action.yaml with inputs, outputs, and all validation steps**

```yaml
name: "Validate release"
description: "Validate a GitHub release for CalVer format, branch targeting, hotfix coherence, and rollback protection"
inputs:
  tag:
    required: false
    description: "Release tag name (e.g., v2026.3.0). Defaults to github.ref_name"
    default: ${{ github.ref_name }}

outputs:
  version:
    description: "Validated tag without v prefix (e.g., 2026.3.1)"
    value: ${{ steps.parse.outputs.version }}
  year:
    description: "Year component (e.g., 2026)"
    value: ${{ steps.parse.outputs.year }}
  minor:
    description: "Minor component (e.g., 3)"
    value: ${{ steps.parse.outputs.minor }}
  patch:
    description: "Patch component (e.g., 1)"
    value: ${{ steps.parse.outputs.patch }}
  is-hotfix:
    description: "true if released from a hotfix/* branch"
    value: ${{ steps.branch.outputs.is-hotfix }}

runs:
  using: composite
  steps:
    - name: Validate CalVer format
      id: parse
      shell: bash
      run: |
        set -e
        TAG="${{ inputs.tag }}"

        if [[ ! "$TAG" =~ ^v[0-9]{4}\.[0-9]+\.[0-9]+$ ]]; then
          echo "ERROR: Tag '$TAG' does not match CalVer format v<YEAR>.<MINOR>.<PATCH>"
          exit 1
        fi

        VERSION="${TAG#v}"
        YEAR=$(echo "$VERSION" | cut -d. -f1)
        MINOR=$(echo "$VERSION" | cut -d. -f2)
        PATCH=$(echo "$VERSION" | cut -d. -f3)

        echo "version=$VERSION" >> "$GITHUB_OUTPUT"
        echo "year=$YEAR" >> "$GITHUB_OUTPUT"
        echo "minor=$MINOR" >> "$GITHUB_OUTPUT"
        echo "patch=$PATCH" >> "$GITHUB_OUTPUT"

        echo "Parsed tag: year=$YEAR minor=$MINOR patch=$PATCH"

    - name: Validate year is not in the past
      shell: bash
      run: |
        set -e
        TAG_YEAR="${{ steps.parse.outputs.year }}"
        CURRENT_YEAR=$(date +%Y)

        if [ "$TAG_YEAR" -lt "$CURRENT_YEAR" ]; then
          echo "ERROR: Tag year $TAG_YEAR is in the past (current year: $CURRENT_YEAR)"
          exit 1
        fi

        echo "Year check passed: $TAG_YEAR >= $CURRENT_YEAR"

    - name: Validate release branch
      id: branch
      shell: bash
      run: |
        set -e
        TARGET="${{ github.event.release.target_commitish }}"

        if [ "$TARGET" = "main" ]; then
          echo "is-hotfix=false" >> "$GITHUB_OUTPUT"
          echo "Branch check passed: target is main (feature release)"
        elif [[ "$TARGET" == hotfix/* ]]; then
          echo "is-hotfix=true" >> "$GITHUB_OUTPUT"
          echo "Branch check passed: target is $TARGET (hotfix release)"
        else
          echo "ERROR: Releases must target 'main' or 'hotfix/*' branches, got '$TARGET'"
          exit 1
        fi

    - name: Validate hotfix-patch coherence
      shell: bash
      run: |
        set -e
        IS_HOTFIX="${{ steps.branch.outputs.is-hotfix }}"
        PATCH="${{ steps.parse.outputs.patch }}"
        TARGET="${{ github.event.release.target_commitish }}"

        if [ "$IS_HOTFIX" = "false" ] && [ "$PATCH" -ne 0 ]; then
          echo "ERROR: Feature releases from 'main' must have patch version 0, got $PATCH"
          exit 1
        fi

        if [ "$IS_HOTFIX" = "true" ] && [ "$PATCH" -eq 0 ]; then
          echo "ERROR: Hotfix releases must have patch version > 0, got 0"
          exit 1
        fi

        echo "Hotfix-patch coherence check passed"

    - name: Rollback protection
      shell: bash
      run: |
        set -e
        LATEST_TAG=$(git tag --list 'v*' --sort=-v:refname | head -1)

        if [ -z "$LATEST_TAG" ]; then
          echo "First release, skipping rollback check"
          exit 0
        fi

        if ! git merge-base --is-ancestor "$LATEST_TAG" "$GITHUB_SHA"; then
          echo "ERROR: Tag ${{ inputs.tag }} is based on a commit older than $LATEST_TAG. Releases must not roll back production."
          exit 1
        fi

        echo "Rollback protection passed: $GITHUB_SHA is a descendant of $LATEST_TAG"
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('validate-release/action.yaml'))"`
Expected: No output (valid YAML)

- [ ] **Step 3: Commit**

```bash
git add validate-release/action.yaml
git commit -m "feat: add validate-release composite action

CalVer format, year, branch, hotfix-patch coherence,
and rollback protection checks for production releases."
```

---

### Task 2: Create `update-production-tag/action.yaml`

**Files:**
- Create: `update-production-tag/action.yaml`

- [ ] **Step 1: Create the action.yaml**

```yaml
name: "Update production tag"
description: "Force-update the floating production tag to the current commit after a successful production deployment"
inputs:
  token:
    required: true
    description: "GitHub token with push permissions for force-pushing the tag"

runs:
  using: composite
  steps:
    - name: Update production tag
      shell: bash
      run: |
        set -e
        git config user.name "github-actions[bot]"
        git config user.email "github-actions[bot]@users.noreply.github.com"
        git tag -f production "${{ github.sha }}"
        git push "https://x-access-token:${{ inputs.token }}@github.com/${{ github.repository }}.git" production --force
        echo "Updated production tag to ${{ github.sha }}"
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('update-production-tag/action.yaml'))"`
Expected: No output (valid YAML)

- [ ] **Step 3: Commit**

```bash
git add update-production-tag/action.yaml
git commit -m "feat: add update-production-tag composite action

Force-updates floating production tag after successful deployment."
```

---

### Task 3: Final review and verification

- [ ] **Step 1: Verify both actions exist and have valid structure**

Run: `ls -la validate-release/action.yaml update-production-tag/action.yaml`
Expected: Both files listed

- [ ] **Step 2: Verify YAML structure matches repo conventions**

Check: inputs use kebab-case, outputs reference step IDs correctly, all steps have `shell: bash`, `set -e` in run blocks.

- [ ] **Step 3: Verify git log shows clean commits**

Run: `git log --oneline -5`
Expected: Two new commits for the two actions
