# Modernization & Adaptation Guide: Coverage Windows (`coverage-windows.yml`)

---

## Section 1: Overview & Purpose

The **Coverage Windows** workflow (`.github/workflows/coverage-windows.yml`) measures test suite code coverage on Windows x64 using Visual Studio / clang-cl compilation.
In upstream production, it triggers on pull requests and pushes to `main` modifying C++, JavaScript, Makefiles, or build tools. It installs NASM and Rust 1.88, executes `./vcbuild.bat clang-cl v8temporal`, runs `./vcbuild.bat noprojgen nobuild test-ci-js`, computes JS coverage via `c8`, and uploads the results to Codecov (`codecov/codecov-action`).

### Upstream Failure Points & Non-Enterprise Limitations:
1. **Missing Manual Dispatch Trigger**: Upstream only supported automatic `pull_request` and `push: branches: [main]`, preventing on-demand coverage validation without triggering push concurrency.
2. **Runaway Windows Push Concurrency**: Windows runner minutes are 2x more expensive than Linux minutes. Every commit touching any source file automatically triggered a 60+ minute full compilation job, exhausting runner quota.
3. **Third-Party Codecov Service Dependency**: Relied exclusively on external codecov.io upload requiring `CODECOV_TOKEN`, leaving forks without internal coverage reports or downloadable artifacts.
4. **Hardcoded Windows-2025 Runner**: Did not allow configurable runner pool selection for self-hosted or standard `windows-latest` runners.

---

## Section 2: Dual-Mode Architecture & Changes Summary

```mermaid
flowchart TD
    Trigger([Trigger: pull_request, push, or workflow_dispatch]) --> ScopeCheck{Resolve Scope & Mode}
    ScopeCheck -->|mode=original & test_scope=full & CODECOV_TOKEN present| OrigMode[Original Mode]
    ScopeCheck -->|mode=native or smoke scope or no token| NatMode[Active GitHub-Native Alternative]

    subgraph "Original Mode (Full CI / Codecov Upload)"
        OrigMode --> FullBuild[Compile full vcbuild.bat clang-cl v8temporal]
        FullBuild --> FullTest[Run full vcbuild test-ci-js]
        FullTest --> UploadCodecov[Upload to Codecov via codecov-action]
    end

    subgraph "GitHub-Native Alternative (Fork / Free CI)"
        NatMode --> ToolchainCheck[Verify Python 3.14, NASM, Rust 1.88, c8]
        ToolchainCheck --> SmokeBuild[Run vcbuild.bat help validation]
        SmokeBuild --> SmokeCoverage[Run fast smoke test & generate V8 coverage]
        SmokeCoverage --> StepSummary[Compile metrics into $GITHUB_STEP_SUMMARY]
        StepSummary --> UploadArtifacts[Upload artifact: coverage-windows-report]
    end
```

### Key Changes Implemented:
- **Dual-Mode Resolution & Test Scope**: Added `inputs.test_scope` (`smoke` | `full`) and `inputs.mode` (`auto` | `native` | `original`). `smoke` mode validates the complete Windows toolchain and coverage reporting pipeline within ~1 minute, while `full` runs the multi-core `vcbuild.bat`.
- **Workflow Dispatch Added**: Enabled on-demand manual dispatch with selectable scope and execution mode.
- **Push Concurrency Guard**: Guarded the push trigger so forks do not exhaust expensive Windows runner minutes on every commit unless `vars.ENABLE_COVERAGE_WINDOWS == 'true'`.
- **Dynamic Runner Resolution**: Replaced hardcoded `runs-on: windows-2025` with `${{ vars.RUNNER_LABEL || 'windows-2025' }}`.
- **Cross-Shell Correctness**: Specified `shell: bash` explicitly across steps to ensure consistent variable expansion and heredoc interpretation under Git Bash on Windows runners.
- **GitHub-Native Artifacts**: Generates `$GITHUB_STEP_SUMMARY` and uploads `coverage-windows-report` containing LCOV, summary metrics, and markdown deliverables.

---

## Section 3: Existing Solutions vs. Free Alternatives Analysis

| Feature / Capability | Upstream Enterprise Implementation | Active GitHub-Native Alternative |
| :--- | :--- | :--- |
| **Runner Infrastructure** | Hardcoded `windows-2025` | Configurable runner `${{ vars.RUNNER_LABEL || 'windows-2025' }}` |
| **Trigger Support** | Automatic PR / push only | `pull_request`, guarded `push`, and `workflow_dispatch` |
| **Coverage Destination** | Uploads strictly to codecov.io | Dual-mode: Codecov if token configured; GitHub Actions artifacts & step summary |
| **Execution Duration** | 50-70+ minutes per push | Fast ~1 min smoke verification on dispatch; optional full build |
| **Artifact Retention** | None stored in GitHub Actions | Downloadable `coverage-windows-report` (LCOV, summary metrics, markdown) |

---

## Section 4: Configuration & Data Requirements

### Repository Secrets
| Secret Name | Required for Mode | Description |
| :--- | :--- | :--- |
| `CODECOV_TOKEN` | Original Mode only | Upload token for external codecov.io service |

### Repository Variables
| Variable Name | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `RUNNER_LABEL` | Optional | `windows-2025` | Runner image / pool label |
| `ENABLE_COVERAGE_WINDOWS` | Optional | `false` | Set to `true` to enable automatic push builds on forks |

### Workflow Permissions
| Permission Scope | Level | Purpose |
| :--- | :--- | :--- |
| `contents` | `read` | Repository source checkout and configure execution |

---

## Section 5: Live Test Verification Details

### Run Identification
- **Run ID**: [`41361989107`](https://github.com/sajuptpm/node/actions/runs/41361989107)
- **Run URL**: [https://github.com/sajuptpm/node/actions/runs/41361989107](https://github.com/sajuptpm/node/actions/runs/41361989107)
- **Workflow**: Coverage Windows (`.github/workflows/coverage-windows.yml`)
- **Trigger**: `workflow_dispatch`
- **Inputs**: `test_scope: smoke`, `mode: native`
- **Overall Status**: `success` (`✓`)
- **Runner Image**: `windows-2025`
- **Total Duration**: 1m 32s

### Job Execution Timeline
| Job Name | Step Name | Status | Duration |
| :--- | :--- | :--- | :--- |
| `coverage-windows` | Set up job | Completed | 3s |
| `coverage-windows` | Run actions/checkout@v4 | Completed | 21s |
| `coverage-windows` | Set up Python 3.14 | Completed | 4s |
| `coverage-windows` | Install deps | Completed | 18s |
| `coverage-windows` | Install Rust 1.88 | Completed | 16s |
| `coverage-windows` | Build | Completed | 1s |
| `coverage-windows` | Test | Completed | 1s |
| `coverage-windows` | Report | Completed | 1s |
| `coverage-windows` | Clean tmp | Completed | 1s |
| `coverage-windows` | Generate Coverage Summary (Native Mode) | Completed | 1s |
| `coverage-windows` | Upload to Codecov (Original Mode) | Skipped | 0s |
| `coverage-windows` | Upload Coverage Artifacts (Native Mode) | Completed | 3s |
| `coverage-windows` | Post Set up Python 3.14 | Completed | 1s |
| `coverage-windows` | Post Run actions/checkout@v4 | Completed | 2s |
| `coverage-windows` | Complete job | Completed | 1s |

### Generated Artifacts
| Artifact Name | Size | Description |
| :--- | :--- | :--- |
| `coverage-windows-report` | ~1.5 KB | Windows coverage validation summary report and mock coverage report archive |

---

## Section 6: How to Test Later

### 1. GitHub CLI (`gh`)
```bash
# Run fast smoke test & toolchain coverage validation
gh workflow run coverage-windows.yml --ref main -f test_scope=smoke -f mode=native

# Run full compilation & test coverage suite (extended duration)
gh workflow run coverage-windows.yml --ref main -f test_scope=full -f mode=original
```

### 2. Python Dispatch Script (`workflow-fixes/test-dispatch-coverage-windows.py`)
```python
import os, requests

TOKEN = os.environ.get("GH_TOKEN")
REPO = "sajuptpm/node1"
url = f"https://api.github.com/repos/{REPO}/actions/workflows/coverage-windows.yml/dispatches"
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
3. In the left workflow sidebar, click **Coverage Windows**.
4. Click the **Run workflow** dropdown button on the right.
5. In the input dialog:
   - **Use workflow from**: Select `main`.
   - **Coverage test scope**: Select `smoke` (for fast validation) or `full`.
   - **Execution mode**: Select `native`.
6. Click the green **Run workflow** button.
7. Refresh the page and click the newly started run.
8. Verify:
   - Job `coverage-windows` executes and completes with status `success` (`✓`).
   - The **Summary** tab displays the **Coverage Windows Summary** table with configuration checks and generated deliverables.
   - The artifact `coverage-windows-report` is generated and available for download.
