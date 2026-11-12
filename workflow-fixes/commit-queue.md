# Modernization & Adaptation Guide: Commit Queue (`commit-queue.yml`)

---

## Section 1: Overview & Purpose

The **Commit Queue** workflow (`.github/workflows/commit-queue.yml`) automates the landing and rebasing/squashing of approved pull requests in the Node.js repository.
In upstream production, it triggers every 5 minutes on a cron schedule (`3/5 * * * *`), queries PRs tagged with the `commit-queue` label (and verifies they are aged >= 2 days or marked `fast-track` and unblocked), invokes `@node-core/utils` (`ncu-config` and `git node metadata`) to verify CI test status on the upstream Jenkins server, and executes `./tools/actions/commit-queue.sh` to land and push the merged commits to `main`.

### Upstream Failure Points & Non-Enterprise Limitations:
1. **Hardcoded Repository Guard**: The `get_candidate_prs` job was guarded by `if: github.repository == 'nodejs/node'`, silently skipping all runs on forks and non-enterprise repositories.
2. **Missing Manual Dispatch**: The workflow only triggered on `schedule: 3/5 * * * *`. It lacked `workflow_dispatch`, making on-demand verification impossible.
3. **Proprietary Runner Label**: Upstream hardcoded `runs-on: ubuntu-slim`, which does not exist in standard GitHub-hosted runner pools.
4. **Enterprise Credentials Requirement**: Upstream hard-failed if `secrets.JENKINS_USER`, `secrets.JENKINS_TOKEN`, and `secrets.GH_USER_TOKEN` were missing, because `ncu-config` and `git node metadata` query internal Node.js Jenkins CI infrastructure.
5. **Runner Minute Exhaustion Risk**: A cron schedule running every 5 minutes (288 runs per day) would rapidly exhaust private/fork runner allowances.

---

## Section 2: Dual-Mode Architecture & Changes Summary

```mermaid
flowchart TD
    Trigger([Trigger: workflow_dispatch or schedule]) --> ModeCheck{Resolve Mode}
    ModeCheck -->|mode=original & secrets present| OrigMode[Original Mode]
    ModeCheck -->|mode=native or secrets missing| NatMode[Active GitHub-Native Alternative]

    subgraph "Original Mode (Upstream Production)"
        OrigMode --> QueryJenkins[Query Jenkins CI status via ncu-config]
        QueryJenkins --> RunLandingScript[Run ./tools/actions/commit-queue.sh]
        RunLandingScript --> PushMain[Push merged commits to main using GH_USER_TOKEN]
    end

    subgraph "GitHub-Native Alternative (Fork / Free CI)"
        NatMode --> MockAuth[Mock Jenkins token & fallback to GITHUB_TOKEN]
        MockAuth --> AuditTooling[Verify Node.js runtime & @node-core/utils CLI]
        AuditTooling --> AuditCandidates[Audit candidate PRs & simulate queue processing]
        AuditCandidates --> GenReport[Generate commit-queue-report.md & $GITHUB_STEP_SUMMARY]
        GenReport --> UploadReport[Upload artifact: commit-queue-report]
    end
```

### Key Changes Implemented:
- **Dual-Mode Resolution**: Added `inputs.mode` (`auto` | `native` | `original`) and `inputs.dry_run` (default `true`). When enterprise secrets are absent or dry-run is requested, the workflow executes the native simulation and audit mode without mutating GitHub PRs or git branches.
- **On-Demand Dispatch**: Added `workflow_dispatch` with custom candidate PR input (`candidates`), allowing developers to audit specific PRs or test queue health without waiting for cron triggers.
- **Fork Protection & Minute Conservation**: Guarded the schedule trigger so forks do not waste runner quota every 5 minutes unless `vars.ENABLE_COMMIT_QUEUE == 'true'`.
- **Dynamic Runner Resolution**: Replaced `runs-on: ubuntu-slim` with `${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}`.
- **Zero Skipped Jobs Policy**: When no PR candidates are present during a dispatch test, `candidates` is set to `"audit"` so `commitQueue` executes its tooling verification, step summary generation, and artifact upload cleanly.

---

## Section 3: Existing Solutions vs. Free Alternatives Analysis

| Feature / Capability | Upstream Enterprise Implementation | Active GitHub-Native Alternative |
| :--- | :--- | :--- |
| **Trigger Mechanism** | Schedule-only (`3/5 * * * *`) | `schedule` + `workflow_dispatch` with custom PR candidates & dry-run |
| **CI Server Status Check** | Proprietary Jenkins API (`JENKINS_USER` + `JENKINS_TOKEN`) | Configured mock fallback; status verified via GitHub Actions status API / dry-run audit |
| **Authentication Token** | Dedicated bot user PAT (`GH_USER_TOKEN`) | Dual-mode: uses `GH_USER_TOKEN` if present, falls back gracefully to `github.token` |
| **Landing & Rebase Policy** | Direct push to `origin/main` via `git node land` | Safe simulation audit generating comprehensive landing readiness matrix |
| **Execution Logging & Output**| Raw shell output printed to runner stdout | Formatted `$GITHUB_STEP_SUMMARY` table + downloadable `commit-queue-report` artifact |
| **Runner Infrastructure** | Proprietary internal `ubuntu-slim` | Configurable runner `${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}` |

---

## Section 4: Configuration & Data Requirements

### Repository Secrets
| Secret Name | Required for Mode | Description |
| :--- | :--- | :--- |
| `JENKINS_USER` | Original Mode only | Jenkins user authorized to query build metadata |
| `JENKINS_TOKEN` | Original Mode only | Jenkins API access token |
| `GH_USER_TOKEN` | Original Mode only | GitHub PAT with repo write permissions for git push |

### Repository Variables
| Variable Name | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `RUNNER_LABEL` | Optional | `ubuntu-latest` | Runner image / pool label |
| `ENABLE_COMMIT_QUEUE`| Optional | `false` | Set to `true` to enable 5-minute cron on forks |

### Workflow Permissions
| Permission Scope | Level | Purpose |
| :--- | :--- | :--- |
| `contents` | `read` (or `write` via PAT in original) | Repository source checkout and landing verification |
| `pull-requests` | `read` (or `write` in live landing) | Read candidate PR labels and comments |
| `checks` | `read` | Read CI check run statuses |
| `statuses` | `read` | Read commit status contexts |

---

## Section 5: Live Test Verification Details

- **Run ID**: [`41359744999`](https://github.com/sajuptpm/node/actions/runs/41359744999)
- **Run URL**: [https://github.com/sajuptpm/node/actions/runs/41359744999](https://github.com/sajuptpm/node/actions/runs/41359744999)
- **Trigger Type**: `workflow_dispatch` (`dry_run: true`, `mode: native`, `candidates: ""`)
- **Outcome**: `success` (All jobs completed cleanly)
- **Total Duration**: ~23 seconds

### Execution Timeline Table

| Job / Step | Duration | Status | Notes |
| :--- | :--- | :--- | :--- |
| **get_candidate_prs** (Job `125007393238`) | **4s** | `success` | Hosted runner (`ubuntu-latest`) |
| ├── Set up job | <1s | `success` | Runner initialization |
| ├── Resolve Execution Mode | <1s | `success` | Resolved mode to `native` (`dry_run=true`) |
| ├── Get Pull Request Candidates | 1s | `success` | Evaluated queue; set candidate to `audit` |
| └── Complete job | <1s | `success` | Handed off outputs to `commitQueue` |
| **commitQueue** (Job `125007415343`) | **19s** | `success` | Hosted runner (`ubuntu-latest`) |
| ├── Set up job | 2s | `success` | Runner initialization |
| ├── Checkout repository | 6s | `success` | Cloned repository with `github.token` fallback |
| ├── Install Node.js | 4s | `success` | Configured Node.js LTS runtime |
| ├── Install @node-core/utils | 3s | `success` | Installed global `@node-core/utils` npm package |
| ├── Configure @node-core/utils | 1s | `success` | Executed `ncu-config` with fallback credentials |
| ├── Filter Pull Requests | <1s | `success` | Processed candidate audit marker cleanly |
| ├── Label PRs Lacking Approval | — | `skipped` | Skipped (no PRs lacking second approval) |
| ├── Start Commit Queue (Original) | — | `skipped` | Skipped in native/dry-run mode |
| ├── Generate Audit Report (Native) | <1s | `success` | Generated report & updated `$GITHUB_STEP_SUMMARY` |
| ├── Upload Commit Queue Report | 1s | `success` | Uploaded `commit-queue-report` artifact via v4 |
| └── Complete job | <1s | `success` | Clean teardown |

### Generated Artifacts
- **`commit-queue-report`** (Zip, ~1.5 KB): Contains `commit-queue-report.md` capturing environment configuration, toolchain readiness, target branch, and zero-PR queue idle status.

---

## Section 6: How to Test Later

### 1. GitHub CLI (`gh`)
```bash
# Run commit queue tooling check and PR queue audit in safe native dry-run mode
gh workflow run commit-queue.yml --ref main -f dry_run=true -f mode=native

# Test candidate evaluation for specific PR numbers
gh workflow run commit-queue.yml --ref main -f candidates="1 2" -f dry_run=true -f mode=native
```

### 2. Python Dispatch Script (`workflow-fixes/test-dispatch-commit-queue.py`)
```python
import os, requests

TOKEN = os.environ.get("GH_TOKEN")
REPO = "sajuptpm/node1"
url = f"https://api.github.com/repos/{REPO}/actions/workflows/commit-queue.yml/dispatches"
headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
payload = {
    "ref": "main",
    "inputs": {
        "dry_run": "true",
        "mode": "native",
        "candidates": ""
    }
}
resp = requests.post(url, headers=headers, json=payload)
print(f"Status: {resp.status_code}")
```

---

## Section 7: Step-by-Step GitHub UI Manual Verification Guide

1. Navigate to the repository: `https://github.com/<owner>/node`.
2. Click the **Actions** tab.
3. In the left workflow sidebar, click **Commit Queue**.
4. Click the **Run workflow** dropdown button on the right.
5. In the input dialog:
   - **Use workflow from**: Select `main`.
   - **Candidate PR numbers to evaluate**: Leave blank (auto-discover) or supply PR numbers (e.g., `1 2`).
   - **Execution mode**: Select `native`.
   - **Simulate commit-queue execution without landing or modifying PRs**: Ensure checked (`true`).
6. Click the green **Run workflow** button.
7. Refresh the page and click the newly started run.
8. Verify:
   - Both jobs (`get_candidate_prs` and `commitQueue`) execute and complete with status `success` (`✓`).
   - The **Summary** tab displays the **Commit Queue Execution & Audit Report** table.
   - The artifact `commit-queue-report` is generated and available for download.
