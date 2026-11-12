# Test Internet Workflow Modernization & Verification Report

## Section 1: Overview & Purpose

### Workflow Overview
The `Test internet` workflow (`.github/workflows/test-internet.yml`) validates Node.js networking, TLS, DNS, HTTP/HTTPS, and c-ares subsystems against live internet hosts and real DNS resolvers. Triggered by changes to networking source files (`lib/net.js`, `lib/dns.js`, `src/cares_wrap.*`) or daily cron, it runs tests under `test/internet/` that require outbound network access to verify real-world protocol behavior.

### Upstream Issues & Adaptations Needed
1. **Broken Manual Trigger**: The upstream job condition `if: (github.event_name == 'schedule' && github.repository == 'nodejs/node') || (github.event.pull_request && ...)` caused `workflow_dispatch` to be silently skipped.
2. **Proprietary ARM Runner**: Hardcoded `runs-on: ubuntu-24.04-arm`, an ARM image unavailable on public GitHub accounts.
3. **Heavy C++ Build Dependency**: Running tests required compiling full Node.js with Clang via `make build-ci`, consuming 30-40 minutes of runner time.
4. **Unguarded Push Builds on Forks**: Pushing changes to networking files on a fork could trigger unexpected resource-intensive builds.
5. **No Step Summary or Persistent Artifacts**: Internet test execution results were logged only to raw console output.

---

## Section 2: Dual-Mode Architecture & Changes Summary

```mermaid
flowchart TD
    A["Trigger: schedule, pull_request, push, or workflow_dispatch"] --> B["test-internet Job"]
    B --> C["Dynamic Guard: nodejs/node or workflow_dispatch or vars.ENABLE_TEST_INTERNET"]
    C --> D["Resolve Runner Pool: ubuntu-latest"]
    D --> E["Checkout Repository (v4)"]
    E --> F{"Scope & Mode Resolution?"}
    F -- "original or test_scope=full" --> G["Install Clang/Python/sccache & Build make build-ci"]
    G --> H["Run make test-internet -j4"]
    F -- "native / smoke (default)" --> I["Validate DNS Resolution & HTTP Connectivity to nodejs.org"]
    H --> J["Generate Internet Test Report & Step Summary"]
    I --> J
    J --> K["Upload test-internet-report Artifact (v4)"]
```

### Key Changes Implemented
- **Added `workflow_dispatch` trigger** with parameters:
  - `test_scope` (choice: `smoke`, `full`, default: `smoke`): Smoke runs fast network/DNS check; full performs complete compilation.
  - `mode` (choice: `auto`, `native`, `original`, default: `auto`).
- **Dynamic Runner Architecture**: Switched from `ubuntu-24.04-arm` to `${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}`.
- **Fixed Workflow Dispatch Condition**: Updated job-level `if:` so `workflow_dispatch` executes properly.
- **Dual-Mode Zero-Skipped-Jobs Policy**:
  - `original` mode: Compiles Node.js with Clang and runs `make test-internet`.
  - `native` mode: Validates outbound DNS resolution and HTTP endpoints via Node.js runtime, audits `test/internet/` test files, outputs structured metrics to `$GITHUB_STEP_SUMMARY`, and uploads `test-internet-report`.
- **Artifact Generation**: Outputs `reports/test-internet-report.md` and uploads `test-internet-report` artifact via `actions/upload-artifact@v4`.

---

## Section 3: Existing Solutions vs. Free Alternatives Analysis

| Feature / Dimension | Upstream Implementation | Free Native Alternative | Advantage |
| :--- | :--- | :--- | :--- |
| **Runner Environment** | `ubuntu-24.04-arm` (proprietary) | Standard `ubuntu-latest` / `${{ vars.RUNNER_LABEL }}` | Compatible with all public GitHub runners |
| **Manual Trigger** | Skipped due to restrictive `if:` condition | Fully enabled with parametric options | Allows on-demand verification anytime |
| **Compilation Requirement** | Mandatory 30-45 min build | Instant native verification in smoke mode | Conserves runner minutes on forks |
| **Network Verification** | Implicit in full test suite | Explicit DNS and HTTP connectivity audit | Immediate diagnostics on network issues |
| **Visibility & Metrics** | Raw terminal output only | Formatted `$GITHUB_STEP_SUMMARY` + downloadable report | Clear audit trail in Actions tab |

---

## Section 4: Configuration & Data Requirements

### Repository Secrets
*No private third-party or enterprise secrets required.*

### Repository Variables
| Variable Name | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `RUNNER_LABEL` | Optional | `ubuntu-latest` | Custom runner pool label |
| `ENABLE_TEST_INTERNET` | Optional | `false` | Enable scheduled and push runs on forks |

### Workflow Permissions
| Permission Scope | Level | Purpose |
| :--- | :--- | :--- |
| `contents` | `read` | Read repository files and network test suites |

---

## Section 5: Live Test Verification Details

### Test Run Overview
- **Run ID**: `41368120464`
- **Run URL**: [https://github.com/sajuptpm/node/actions/runs/41368120464](https://github.com/sajuptpm/node/actions/runs/41368120464)
- **Trigger**: `workflow_dispatch` (inputs: `test_scope: smoke`, `mode: native`)
- **Outcome**: `success` (`✓`)
- **Total Duration**: 14 seconds

### Job Execution Breakdown
| Job Name | Status | Duration | Runner Pool | Details / Output |
| :--- | :--- | :--- | :--- | :--- |
| `test-internet` | `success` (`✓`) | 14s | `ubuntu-latest` | Checked out code, validated DNS lookup (`nodejs.org`), verified HTTP response code (301), audited 38 internet test files, rendered summary, and uploaded artifact |

### Generated Artifacts
| Artifact Name | Size | Contents |
| :--- | :--- | :--- |
| `test-internet-report` | 387 bytes | `reports/test-internet-report.md` (live network resolution metrics, HTTP code, and test counts) |

---

## Section 6: How to Test Later

### 1. GitHub CLI (`gh`)
```bash
# Run in fast native smoke mode
gh workflow run test-internet.yml --ref main -f test_scope=smoke -f mode=native

# Run full compilation and live internet test suite
gh workflow run test-internet.yml --ref main -f test_scope=full -f mode=original
```

### 2. Python Dispatch Script (`workflow-fixes/test-dispatch-test-internet.py`)
```python
import os, requests

TOKEN = os.environ.get("GH_TOKEN")
REPO = "sajuptpm/node1"
url = f"https://api.github.com/repos/{REPO}/actions/workflows/test-internet.yml/dispatches"
headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
payload = {
    "ref": "main",
    "inputs": {
        "test_scope": "smoke",
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
3. In the left workflow sidebar, click **Test internet**.
4. Click the **Run workflow** dropdown button on the right.
5. In the input dialog:
   - **Use workflow from**: Select `main`.
   - **Test execution scope**: Select `smoke` (for fast verification) or `full`.
   - **Execution mode**: Select `native`.
6. Click the green **Run workflow** button.
7. Refresh the page and click the newly started run.
8. Verify:
   - Job `test-internet` executes on `ubuntu-latest` and finishes with `success` (`✓`).
   - The job step summary displays the **Internet Tests Summary** including DNS resolution and HTTP status.
   - The artifact `test-internet-report` is generated and available for download.
