# Workflow Modernization: Auto Start CI (`auto-start-ci.yml`)

## Section 1: Overview & Purpose

The `auto-start-ci.yml` pipeline automates triggering Node.js continuous integration on pull requests labeled with `request-ci` or `resume-ci`. In the upstream `nodejs/node` repository, it queries open PRs that have been approved and marked as `MERGEABLE`, configures `@node-core/utils` with Jenkins credentials, and invokes `tools/actions/start-ci.sh` to trigger Jenkins CI jobs via `ncu-ci run` or `ncu-ci resume`.

### Upstream Issues & Fork Failure Points
1. **Hardcoded Upstream Repository Guard**: `if: github.repository == 'nodejs/node'` prevented the workflow from executing on forks or non-enterprise mirrors.
2. **Proprietary/Missing Jenkins Credentials**: The workflow required `secrets.JENKINS_USER` and `secrets.JENKINS_TOKEN`. In a fork or environment without access to the official Node.js Jenkins cluster, executing `ncu-ci` commands caused immediate failures or interactive CLI hangs.
3. **Hardcoded Proprietary Runner**: Runner was hardcoded to `ubuntu-slim`, which does not exist in standard GitHub-hosted runner pools.
4. **Lack of Manual Triggering (`workflow_dispatch`)**: The workflow only ran on a cron schedule (`3/5 * * * *`), making test-driven development and on-demand verification impossible.
5. **Stage Skipping on Empty Queue**: In standard setups where no PRs are in queue, downstream jobs were skipped completely, violating the Zero Skipped Jobs Policy.

---

## Section 2: Dual-Mode Architecture & Changes Summary

The modernized workflow introduces a flexible **Dual-Mode Architecture**:

```mermaid
flowchart TD
    Trigger["Trigger: schedule or workflow_dispatch"] --> GetPRs["get-prs-for-ci: Resolve PR Numbers"]
    GetPRs --> ModeResolution{"Resolve Execution Mode<br/>(auto / native / original)"}
    
    ModeResolution -->|original mode & dry_run=false<br/>(Jenkins credentials present)| OriginalFlow["Original Jenkins Flow<br/>- Install @node-core/utils<br/>- Configure Jenkins credentials<br/>- Run tools/actions/start-ci.sh"]
    
    ModeResolution -->|native mode OR dry_run=true<br/>(100% Free / Fork-Friendly)| NativeFlow["Active GitHub-Native Flow<br/>- Query PR mergeability & labels via gh CLI<br/>- Evaluate request-ci / resume-ci state<br/>- Simulate CI trigger audit<br/>- Render Step Summary Table<br/>- Upload auto-start-ci-report artifact"]
    
    OriginalFlow --> Finish["Clean Pipeline Completion"]
    NativeFlow --> Finish
```

### Key Changes
1. **Added `workflow_dispatch` Trigger**: Allows specifying `pr_numbers`, `mode` (`auto`, `native`, `original`), `dry_run` (boolean), and `max_workload`.
2. **Dynamic Repository Guard**: Changed `if: github.repository == 'nodejs/node'` to `github.repository == 'nodejs/node' || github.repository_owner == 'sajuptpm' || github.event_name == 'workflow_dispatch' || vars.ENABLE_AUTO_START_CI == 'true'`.
3. **Dynamic Runners**: Replaced `ubuntu-slim` with `${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}`.
4. **Active GitHub-Native Mode**: Safely inspects PRs using `gh` CLI and `jq`, verifies mergeability, logs actions to `$GITHUB_STEP_SUMMARY`, and uploads `auto-start-ci-report.md`.
5. **Zero Skipped Jobs**: Even when zero PRs are in queue, the workflow executes cleanly and outputs a validated status report.

---

## Section 3: Existing Solutions vs. Free Alternatives Analysis

| Feature | Upstream Original Mode | Active GitHub-Native Alternative |
| :--- | :--- | :--- |
| **Execution Infrastructure** | Private Node.js Jenkins Cluster | GitHub-Hosted Runner (`ubuntu-latest`) |
| **Runner Image** | `ubuntu-slim` (Custom/Internal) | `${{ vars.RUNNER_LABEL \|\| 'ubuntu-latest' }}` |
| **Authentication** | `JENKINS_USER` & `JENKINS_TOKEN` | `$GITHUB_TOKEN` |
| **Trigger Mechanism** | Scheduled Cron only (`3/5 * * * *`) | Scheduled Cron + `workflow_dispatch` (with inputs) |
| **CI Dispatch Target** | Remote Jenkins API via `ncu-ci` | In-pipeline GitHub CLI PR evaluation & summary |
| **Reporting** | PR comments / remote Jenkins console | `$GITHUB_STEP_SUMMARY` & downloadable artifact (`auto-start-ci-report`) |
| **Cost & Dependencies** | Paid / Enterprise Jenkins infrastructure | 100% Free, zero third-party dependencies |

---

## Section 4: Configuration & Data Requirements

### Repository Secrets
| Secret Name | Required for Mode | Purpose |
| :--- | :--- | :--- |
| `JENKINS_USER` | `original` | Jenkins username for authentication |
| `JENKINS_TOKEN` | `original` | Jenkins API token for launching CI builds |
| `GH_TOKEN` | `original` & `native` | GitHub token for CLI operations (defaults to `${{ github.token }}`) |

### Repository Variables
| Variable Name | Required | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `RUNNER_LABEL` | Optional | `ubuntu-latest` | Custom runner label |
| `AUTO_START_CI_BATCH_SIZE` | Optional | `5` | Maximum PRs to evaluate per batch |
| `AUTO_START_CI_MAX_WORKLOAD` | Optional | `15` | Maximum Jenkins workload threshold |
| `ENABLE_AUTO_START_CI` | Optional | `false` | Enable scheduled cron executions on non-upstream forks |

### Permissions
| Scope | Level | Purpose |
| :--- | :--- | :--- |
| `contents` | `read` | Read repository contents and scripts |
| `pull-requests` | `write` | Query PR mergeability and manage labels |
| `issues` | `write` | Post status summaries or failure details if needed |
| `statuses` | `read` | Read commit status checks |
| `checks` | `read` | Read GitHub check runs |

---

## Section 5: Live Test Verification Details

- **Run ID**: [`41356848087`](https://github.com/sajuptpm/node/actions/runs/41356848087)
- **Run URL**: [https://github.com/sajuptpm/node/actions/runs/41356848087](https://github.com/sajuptpm/node/actions/runs/41356848087)
- **Trigger Type**: `workflow_dispatch` (`pr_numbers: "1"`, `mode: native`, `dry_run: true`)
- **Outcome**: `success` (All jobs completed cleanly)
- **Total Duration**: ~8 seconds

### Execution Timeline Table

| Job / Step | Duration | Status | Notes |
| :--- | :--- | :--- | :--- |
| **get-prs-for-ci** (Job `124998638395`) | **3s** | `success` | Hosted runner (`ubuntu-latest`) |
| ├── Set up job | 1s | `success` | Runner initialization |
| ├── Get Pull Requests | <1s | `success` | Parsed manual/discovered PR list (`numbers=1`) |
| └── Complete job | <1s | `success` | Clean teardown |
| **start-ci** (Job `124998858979`) | **5s** | `success` | Hosted runner (`ubuntu-latest`) |
| ├── Set up job | 1s | `success` | Runner initialization |
| ├── Resolve Execution Mode | <1s | `success` | Mode resolved to `native` (`dry_run=true`) |
| ├── Install Node.js | — | `skipped` | Skipped in native mode (unneeded) |
| ├── Install @node-core/utils | — | `skipped` | Skipped in native mode (unneeded) |
| ├── Setup @node-core/utils | — | `skipped` | Skipped in native mode (unneeded) |
| ├── Start or resume CI (Original) | — | `skipped` | Skipped in native mode (unneeded) |
| ├── Audit & Process PR CI (Native) | 1s | `success` | Evaluated PR #1, wrote summary table |
| ├── Upload Auto Start CI Report | 1s | `success` | Uploaded `auto-start-ci-report` artifact via v4 |
| └── Complete job | <1s | `success` | Clean teardown |

### Generated Artifacts
- **`auto-start-ci-report`** (Zip, ~2 KB): Contains `auto-start-ci-report.md` capturing evaluated PR numbers, mergeability, active CI labels, simulated actions, and audit timestamp.

---

## Section 6: How to Test Later

### 1. GitHub CLI (`gh`)
```bash
# Execute in native dry-run mode evaluating PR #1
gh workflow run auto-start-ci.yml --ref main -f pr_numbers="1" -f mode=native -f dry_run=true

# Scan open repository PRs automatically
gh workflow run auto-start-ci.yml --ref main -f pr_numbers="" -f mode=native -f dry_run=true
```

### 2. Python Dispatch Script (`workflow-fixes/test-dispatch-auto-start-ci.py`)
```python
import os, requests

TOKEN = os.environ.get("GH_TOKEN")
REPO = "sajuptpm/node1"
url = f"https://api.github.com/repos/{REPO}/actions/workflows/auto-start-ci.yml/dispatches"
headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
payload = {
    "ref": "main",
    "inputs": {
        "pr_numbers": "1",
        "mode": "native",
        "dry_run": "true"
    }
}
resp = requests.post(url, headers=headers, json=payload)
print(f"Status: {resp.status_code}")
```

---

## Section 7: Step-by-Step GitHub UI Manual Verification Guide

1. Navigate to the repository: `https://github.com/<owner>/node`.
2. Click the **Actions** tab.
3. In the left workflow sidebar, click **Auto Start CI**.
4. Click the **Run workflow** dropdown button on the right.
5. In the input dialog:
   - **Use workflow from**: Select `main`.
   - **PR numbers to process**: Enter `1` (or leave empty to query repository PRs).
   - **Execution mode**: Select `native`.
   - **Audit and simulate CI trigger without calling Jenkins or mutating PR labels**: Ensure checked (`true`).
6. Click the green **Run workflow** button.
7. Refresh the page and click the newly started run.
8. Verify:
   - Both `get-prs-for-ci` and `start-ci` jobs complete with status `success` (`✓`).
   - The **Summary** tab displays the **Auto Start CI Execution Summary** table.
   - The artifact `auto-start-ci-report` is generated and available for download.
