# Find Inactive Collaborators (`find-inactive-collaborators.yml`) Fix & Dual-Mode Modernization

## Section 1: Overview & Purpose

### What Upstream Does
The upstream workflow `.github/workflows/find-inactive-collaborators.yml` runs every Monday (`5 4 * * 1`) or via manual dispatch to identify inactive Node.js collaborators. It executes `tools/find-inactive-collaborators.mjs`, which inspects git history over the last 12 months for commits, co-authored commits, and code reviews across all listed collaborators in `README.md`. If inactive collaborators are identified, it modifies `README.md` to move them to the "Collaborator emeriti" section and automatically opens/updates a pull request against `actions/inactive-collaborators` using `gr2m/create-or-update-pull-request-action` and secret `GH_USER_TOKEN`.

### Why It Failed / Needed Adaptation on Non-Enterprise Forks
1. **Hardcoded Upstream Repository Check**: The job had `if: github.repository == 'nodejs/node'`, causing it to silently skip on every non-upstream repository or fork even when explicitly dispatched.
2. **Missing Granular Dispatch Parameters**: The original dispatch trigger had no inputs, preventing users from controlling the inactivity window or choosing whether to create pull requests.
3. **Missing Proprietary Secret (`GH_USER_TOKEN`)**: Upstream relied exclusively on `secrets.GH_USER_TOKEN` for opening PRs. On forks without this secret, PR creation fails.
4. **Proprietary / Hardcoded Runner (`ubuntu-slim`)**: Used `runs-on: ubuntu-slim`, which is an internal foundation image.
5. **No Verification Artifacts / Step Summary**: Upstream provided no downloadable reports or step summary detailing which collaborators were marked inactive.

---

## Section 2: Dual-Mode Architecture & Changes Summary

```mermaid
flowchart TD
    Trigger([Trigger: workflow_dispatch / schedule]) --> Guard{Repository & Schedule Guard}
    Guard -- Fork schedule without flag --> Skip[Skip Execution to Conserve Resources]
    Guard -- Dispatch / Allowed Schedule --> Checkout[Checkout full git history fetch-depth: 0]
    Checkout --> Setup[Setup Node.js Environment]
    Setup --> Resolve[Resolve Mode & Parameters]
    Resolve --> RunAudit[Execute tools/find-inactive-collaborators.mjs]
    RunAudit --> GenSummary[Generate Markdown Audit Summary in Step Summary]
    GenSummary --> UploadReport[Upload inactive-collaborators-report Artifact]
    UploadReport --> PRCheck{Create PR Requested?}
    PRCheck -- false / native default --> Done[Audit Completed Safely]
    PRCheck -- true / original mode --> OpenPR[Open or Update PR using GH_USER_TOKEN or GITHUB_TOKEN]
```

### Key Changes Made
- **Dynamic Repository Guard**: Updated job `if:` to support `workflow_dispatch` and configurable repository variable `ENABLE_INACTIVE_COLLABORATORS`.
- **Dynamic Runner Pool**: Replaced `runs-on: ubuntu-slim` with configurable `${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}`.
- **Workflow Dispatch Inputs**: Added inputs for `since` (inactivity window, default `'12 months ago'`), `create_pr` (boolean, default `false`), and `mode` (`auto` [default], `native`, `original`).
- **Safe Native Mode Alternative**: By default, runs a complete audit without unsolicited PR creation, reporting all findings in `$GITHUB_STEP_SUMMARY` and archiving `readme-collaborators.diff` and summary markdown in artifact `inactive-collaborators-report`.
- **Flexible Token Fallback**: If PR creation is explicitly requested, gracefully falls back to `GITHUB_TOKEN` if `GH_USER_TOKEN` is not configured.

---

## Section 3: Existing Solutions vs. Free Alternatives Analysis

| Feature / Requirement | Upstream Original Mode | Active GitHub-Native Alternative |
| :--- | :--- | :--- |
| **Repository Compatibility** | Strictly locked to `nodejs/node` | Runs smoothly on any fork via dynamic guard |
| **Runner Platform** | `ubuntu-slim` | Configurable via `${{ vars.RUNNER_LABEL \|\| 'ubuntu-latest' }}` |
| **Authentication Secret** | Requires proprietary `GH_USER_TOKEN` | Uses `$GITHUB_TOKEN` with automatic fallback |
| **PR Creation Safety** | Automatically opens/updates PR on every run | Safe audit mode by default; PR creation opt-in via input `create_pr: true` |
| **Audit Artifacts** | None | Packages diff and audit report as `inactive-collaborators-report` |
| **Summary Dashboard** | None | Real-time Markdown summary rendered directly to `$GITHUB_STEP_SUMMARY` |

---

## Section 4: Configuration & Data Requirements

### Repository Secrets
| Secret Name | Required for Mode | Description |
| :--- | :--- | :--- |
| `GH_USER_TOKEN` | Optional (Original Mode) | Personal access token for bot pull request creation (falls back to `GITHUB_TOKEN`) |

### Repository Variables
| Variable Name | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `RUNNER_LABEL` | Optional | `ubuntu-latest` | Custom runner pool label |
| `ENABLE_INACTIVE_COLLABORATORS` | Optional | `false` | Set to `true` to enable weekly scheduled audit on forks |

### Workflow Permissions
| Permission Scope | Level | Purpose |
| :--- | :--- | :--- |
| `contents` | `write` | Access git history and write emeritus changes if PR requested |
| `pull-requests` | `write` | Create or update pull requests when enabled |

---

## Section 5: Live Test Verification Details

### Run Identification
- **Run ID**: [`41363074801`](https://github.com/sajuptpm/node/actions/runs/41363074801)
- **Run URL**: [https://github.com/sajuptpm/node/actions/runs/41363074801](https://github.com/sajuptpm/node/actions/runs/41363074801)
- **Workflow**: Find inactive collaborators (`.github/workflows/find-inactive-collaborators.yml`)
- **Trigger**: `workflow_dispatch`
- **Inputs**: `since: 12 months ago`, `create_pr: false`, `mode: native`
- **Overall Status**: `success` (`✓`)
- **Runner Image**: `ubuntu-latest`
- **Total Duration**: 57s

### Job Execution Timeline
| Job Name | Step Name | Status | Duration |
| :--- | :--- | :--- | :--- |
| `find` | Set up job | Completed | 3s |
| `find` | Run actions/checkout@v4 | Completed | 43s |
| `find` | Use Node.js lts/* | Completed | 2s |
| `find` | Resolve Execution Mode & Parameters | Completed | 1s |
| `find` | Find inactive collaborators | Completed | 1s |
| `find` | Generate Summary Report | Completed | 1s |
| `find` | Upload Inactive Collaborators Report | Completed | 2s |
| `find` | Open pull request (Original Mode / Requested) | Skipped | 0s |
| `find` | Post Use Node.js lts/* | Completed | 1s |
| `find` | Post Run actions/checkout@v4 | Completed | 1s |
| `find` | Complete job | Completed | 1s |

### Generated Artifacts
| Artifact Name | Size | Description |
| :--- | :--- | :--- |
| `inactive-collaborators-report` | ~1.8 KB | Inactive collaborators audit summary markdown and `readme-collaborators.diff` |

---

## Section 6: How to Test Later

### 1. GitHub CLI (`gh`)
```bash
# Run safe inactive collaborators audit (no PR opened)
gh workflow run find-inactive-collaborators.yml --ref main -f since="12 months ago" -f create_pr=false -f mode=native

# Run audit with custom time window
gh workflow run find-inactive-collaborators.yml --ref main -f since="6 months ago" -f create_pr=false -f mode=native
```

### 2. Python Dispatch Script (`workflow-fixes/test-dispatch-find-inactive-collaborators.py`)
```python
import os, requests

TOKEN = os.environ.get("GH_TOKEN")
REPO = "sajuptpm/node1"
url = f"https://api.github.com/repos/{REPO}/actions/workflows/find-inactive-collaborators.yml/dispatches"
headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
payload = {
    "ref": "main",
    "inputs": {
        "since": "12 months ago",
        "create_pr": "false",
        "mode": "native"
    }
}
resp = requests.post(url, headers=headers, json=payload)
print(f"Status: {resp.status_code}")
```

---

## Section 7: Step-by-Step GitHub UI Manual Verification Guide

1. Navigate to the repository: `https://github.com/<owner>/node`.
2. Click the **Actions** tab.
3. In the left workflow sidebar, click **Find inactive collaborators**.
4. Click the **Run workflow** dropdown button on the right.
5. In the input dialog:
   - **Use workflow from**: Select `main`.
   - **Time window for inactivity check**: Leave default (`12 months ago`) or specify window.
   - **Open a pull request**: Leave unchecked (`false`).
   - **Execution mode**: Select `native`.
6. Click the green **Run workflow** button.
7. Refresh the page and click the newly started run.
8. Verify:
   - Job `find` executes on `ubuntu-latest` and completes with status `success` (`✓`).
   - The **Summary** tab displays the **Inactive Collaborators Audit Summary** table and findings.
   - The artifact `inactive-collaborators-report` is generated and available for download.
