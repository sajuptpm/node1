# Modernized CI/CD Workflow: V8 patch update

## Section 1: Overview & Purpose

The `update-v8.yml` workflow checks for upstream patch updates to Google V8 in the release branch tracked by Node.js, uses `@node-core/utils` to bump patch versions, and automatically creates a pull request.

### Why Adaptation Was Required
1. **Hardcoded Repository Guard**: Upstream had `if: github.repository == 'nodejs/node'`, blocking manual runs and scheduled updates in forks.
2. **Proprietary Runner**: Upstream was hardcoded to `runs-on: ubuntu-slim`, which does not exist on standard GitHub Actions.
3. **Missing `workflow_dispatch` Input Schema**: The workflow lacked configurable inputs for testing mode and dry-run safety.
4. **Enterprise Secret Dependency**: Upstream relied exclusively on `secrets.GH_USER_TOKEN` for `peter-evans/create-pull-request`, which is undefined in forks, causing failures when updates were detected.
5. **Outdated Actions**: Actions were pinned to older git commit SHAs rather than updated standard action versions (`actions/checkout@v4`, `actions/setup-node@v4`, `actions/cache@v4`).
6. **No Dry-Run / Audit Mode**: Upstream could not perform non-destructive version audits and verification of updater tooling.

---

## Section 2: Dual-Mode Architecture & Changes Summary

```mermaid
flowchart TD
    Trigger([Trigger: workflow_dispatch / schedule]) --> ConditionCheck{Evaluate Repo Guard & Event}
    ConditionCheck -->|Skipped| EndSkip([End: Skipped on Fork Push])
    ConditionCheck -->|Active| ModeDecision{Mode & Dry Run?}
    ModeDecision -->|Original Mode & Not Dry Run| OriginalFlow[Setup Node.js & @node-core/utils -> Run update-v8-patch.sh -> Open PR via GH_USER_TOKEN/GITHUB_TOKEN]
    ModeDecision -->|Native Mode OR Dry Run| NativeAudit[Inspect deps/v8 v8-version.h -> Extract major.minor.build.patch -> Verify update-v8-patch.sh -> Generate Report]
    OriginalFlow --> Summary[Write Summary & Artifact]
    NativeAudit --> Summary
    Summary --> Done([End: Success])
```

### Key Changes
- **Dynamic Runner Pool**: Replaced `ubuntu-slim` with `${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}`.
- **Fork Resilience**: Added `github.event_name == 'workflow_dispatch' || vars.ENABLE_UPDATE_V8 == 'true'` to the repository guard.
- **Configurable Inputs**: Added `mode` (`auto`, `native`, `original`) and `dry_run` (`true`, `false`).
- **Secret Fallback**: Allows `GITHUB_TOKEN` fallback when `GH_USER_TOKEN` is not defined.
- **Dual-Mode Verification**:
  - **Native Mode / Dry-Run**: Checks current vendored V8 version (`14.6.202.34`) in `deps/v8/include/v8-version.h`, verifies `update-v8-patch.sh`, and produces `reports/v8-update-report.md`.
  - **Original Mode**: Runs live npm installation of `@node-core/utils`, executes git operations, and opens a pull request.
- **Artifact Generation**: Produces `v8-update-report` artifact.

---

## Section 3: Existing Solutions vs. Free Alternatives Analysis

| Feature / Step | Upstream Workflow | Modernized Free GitHub-Native Alternative |
| :--- | :--- | :--- |
| **Runner Infrastructure** | Proprietary `ubuntu-slim` | Configurable standard runner `${{ vars.RUNNER_LABEL \|\| 'ubuntu-latest' }}` |
| **Repository Guard** | Hardcoded to `nodejs/node` only | Dynamic guard supporting manual dispatches and `vars.ENABLE_UPDATE_V8` |
| **Manual Triggering** | Unparameterized `workflow_dispatch:` | Parameterized `mode` and `dry_run` inputs |
| **Pull Request Token** | Requires private `secrets.GH_USER_TOKEN` | Supports `secrets.GH_USER_TOKEN \|\| secrets.GITHUB_TOKEN` with dry-run safety |
| **Version Audit** | Silent console log | Step Summary and downloadable `v8-update-report` artifact |
| **Dependency Updates** | Fails in forks without credentials | Safe dry-run audit inspecting vendored vs upstream versions |

---

## Section 4: Configuration & Data Requirements

### Repository Secrets
| Secret Name | Required | Description |
| :--- | :--- | :--- |
| `GH_USER_TOKEN` | Optional | Personal access token for opening PRs in original mode (defaults to `GITHUB_TOKEN`) |

### Repository Variables
| Variable Name | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `RUNNER_LABEL` | Optional | `ubuntu-latest` | Custom runner pool label |
| `ENABLE_UPDATE_V8` | Optional | `false` | Enable scheduled runs on forks |

### Workflow Permissions
| Permission Scope | Level | Purpose |
| :--- | :--- | :--- |
| `contents` | `write` | Read repo contents and write commits/branches when updating |
| `pull-requests` | `write` | Create or update pull requests |

---

## Section 5: Live Test Verification Details

- **Run ID**: [`41370156681`](https://github.com/sajuptpm/node/actions/runs/41370156681)
- **Run URL**: [https://github.com/sajuptpm/node/actions/runs/41370156681](https://github.com/sajuptpm/node/actions/runs/41370156681)
- **Trigger Type**: `workflow_dispatch` (`mode=native`, `dry_run=true`)
- **Outcome**: `success` (`completed`)
- **Duration**: `14s`

### Execution Timeline Table
| Step / Job Name | Status | Duration | Details |
| :--- | :--- | :--- | :--- |
| `Set up job` | Completed | 2s | Runner initialized on standard `ubuntu-latest` |
| `Run actions/checkout@v4` | Completed | 2s | Checked out repository root at ref `main` |
| `Cache node modules and update-v8` | Skipped | 0s | Bypassed in native dry-run mode |
| `Install Node.js` | Skipped | 0s | Bypassed in native dry-run mode |
| `Install @node-core/utils` | Skipped | 0s | Bypassed in native dry-run mode |
| `Setup Git config` | Skipped | 0s | Bypassed in native dry-run mode |
| `Check and download new V8 version` | Skipped | 0s | Bypassed in native dry-run mode |
| `Create Pull Request` | Skipped | 0s | Bypassed in native dry-run mode |
| `Native V8 Version Audit & Sanity Check` | Completed | 3s | Inspected vendored version (`14.6.202.34`) in `deps/v8/include/v8-version.h` and validated `tools/dep_updaters/update-v8-patch.sh` |
| `Upload V8 Report Artifact` | Completed | 2s | Uploaded `reports/v8-update-report.md` |
| `Complete job` | Completed | 0s | Clean exit code 0 |

### Generated Artifacts
- **Artifact Name**: `v8-update-report`
  - Contents: `reports/v8-update-report.md` (detailed markdown report containing vendored V8 version components, updater script verification, target branch, and audit summary)

---

## Section 6: How to Test Later

### 1. GitHub CLI (`gh`)
```bash
# Run in safe dry-run audit mode
gh workflow run update-v8.yml --ref main -f mode=native -f dry_run=true

# Run full live update check
gh workflow run update-v8.yml --ref main -f mode=original -f dry_run=false
```

### 2. Python Dispatch Script (`workflow-fixes/test-dispatch-update-v8.py`)
```python
import os, requests

TOKEN = os.environ.get("GH_TOKEN")
REPO = "sajuptpm/node1"
url = f"https://api.github.com/repos/{REPO}/actions/workflows/update-v8.yml/dispatches"
headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
payload = {
    "ref": "main",
    "inputs": {
        "mode": "native",
        "dry_run": True
    }
}
resp = requests.post(url, headers=headers, json=payload)
print(f"Status: {resp.status_code}")
```

---

## Section 7: Step-by-Step GitHub UI Manual Verification Guide

1. Navigate to the repository: `https://github.com/<owner>/node`.
2. Click the **Actions** tab.
3. In the left workflow sidebar, click **V8 patch update**.
4. Click the **Run workflow** dropdown button on the right.
5. In the input dialog:
   - **Use workflow from**: Select `main`.
   - **Execution mode**: Select `native` or `auto`.
   - **Dry-run mode**: Keep checked (`true`) for non-destructive audit.
6. Click the green **Run workflow** button.
7. Refresh the page and click the newly started run.
8. Verify:
   - Job `v8-update` executes on `ubuntu-latest` and finishes with `success` (`✓`).
   - The job step summary displays the **V8 Version Summary** showing the vendored V8 version (`14.6.202.34`), updater script status, and audit conclusion.
   - The artifact `v8-update-report` is generated and available for download.
