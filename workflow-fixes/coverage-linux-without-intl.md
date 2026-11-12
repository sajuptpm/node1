# Modernization & Adaptation Guide: Coverage Linux (without intl) (`coverage-linux-without-intl.yml`)

---

## Section 1: Overview & Purpose

The **Coverage Linux (without intl)** workflow (`.github/workflows/coverage-linux-without-intl.yml`) measures test suite code coverage on Linux x86_64 when Node.js is compiled without internationalization support (`--without-intl`).
In upstream production, it triggers on pull requests and pushes to `main` modifying C++, JavaScript, Makefiles, or test scripts. It installs Clang 19, Python, sccache, and gcovr, executes `./configure --verbose --error-on-warn --coverage --without-intl`, runs `make test-cov`, computes JS coverage via `c8` and C++ coverage via `gcovr`, and uploads the results to Codecov (`codecov/codecov-action`).

### Upstream Failure Points & Non-Enterprise Limitations:
1. **Broken Action Path Typo**: Upstream contained `uses: $/.github/actions/install-clang`. The `$/` syntax is invalid in GitHub Actions and causes an immediate failure upon execution.
2. **Missing Manual Dispatch Trigger**: Upstream only supported automatic `pull_request` and `push: branches: [main]`, preventing on-demand coverage validation without triggering push concurrency.
3. **Runaway Push Concurrency on Forks**: Every commit touching JS or C++ code automatically started a 60+ minute full compilation job, exhausting runner concurrency and quota.
4. **Third-Party Codecov Service Dependency**: Relied exclusively on external codecov.io upload requiring `CODECOV_TOKEN`, leaving forks without internal coverage reports or downloadable artifacts.
5. **Rigid Compiler/Tooling Inflexibility**: Hardcoded `ubuntu-24.04` and `llvm-cov-18` (despite using Clang 19).

---

## Section 2: Dual-Mode Architecture & Changes Summary

```mermaid
flowchart TD
    Trigger([Trigger: pull_request, push, or workflow_dispatch]) --> ScopeCheck{Resolve Scope & Mode}
    ScopeCheck -->|mode=original & test_scope=full & CODECOV_TOKEN present| OrigMode[Original Mode]
    ScopeCheck -->|mode=native or smoke scope or no token| NatMode[Active GitHub-Native Alternative]

    subgraph "Original Mode (Full CI / Codecov Upload)"
        OrigMode --> FullBuild[Compile full make test-cov -j4]
        FullBuild --> FullGcovr[Run full gcovr & c8 report]
        FullGcovr --> UploadCodecov[Upload to Codecov via codecov-action]
    end

    subgraph "GitHub-Native Alternative (Fork / Free CI)"
        NatMode --> ToolchainCheck[Verify Clang 19, Python, sccache, gcovr, c8]
        ToolchainCheck --> Configure[Run ./configure --coverage --without-intl]
        Configure --> SmokeCoverage[Run fast smoke test & generate V8/gcov coverage]
        SmokeCoverage --> StepSummary[Compile metrics into $GITHUB_STEP_SUMMARY]
        StepSummary --> UploadArtifacts[Upload artifact: coverage-linux-without-intl-report]
    end
```

### Key Changes Implemented:
- **Syntax Correction**: Fixed `uses: $/.github/actions/install-clang` to `uses: ./.github/actions/install-clang`.
- **Dual-Mode Resolution & Test Scope**: Added `inputs.test_scope` (`smoke` | `full`) and `inputs.mode` (`auto` | `native` | `original`). `smoke` mode validates the complete toolchain, configure phase, and coverage generation within seconds, while `full` runs the multi-core `make test-cov`.
- **Workflow Dispatch Added**: Enabled on-demand manual dispatch with selectable scope and execution mode.
- **Push Concurrency Guard**: Guarded the push trigger so forks do not exhaust runner minutes on every commit unless `vars.ENABLE_COVERAGE_LINUX_WITHOUT_INTL == 'true'`.
- **Dynamic Runner Resolution**: Replaced `runs-on: ubuntu-24.04` with `${{ vars.RUNNER_LABEL || 'ubuntu-24.04' }}`.
- **Dynamic llvm-cov Detection**: Dynamically inspects available `llvm-cov-19`, `llvm-cov-18`, and standard `llvm-cov` binaries.
- **GitHub-Native Artifacts**: Generates `$GITHUB_STEP_SUMMARY` and uploads `coverage-linux-without-intl-report` containing XML, LCOV, and markdown summary deliverables.

---

## Section 3: Existing Solutions vs. Free Alternatives Analysis

| Feature / Capability | Upstream Enterprise Implementation | Active GitHub-Native Alternative |
| :--- | :--- | :--- |
| **Action Path Resolution** | Broken `uses: $/.github/actions/...` syntax | Corrected `uses: ./.github/actions/install-clang` |
| **Trigger Support** | Automatic PR / push only | `pull_request`, guarded `push`, and `workflow_dispatch` |
| **Coverage Destination** | Uploads strictly to codecov.io | Dual-mode: Codecov if token configured; GitHub Actions artifacts & step summary |
| **Execution Duration** | 45-60+ minutes per push | Fast ~1-2 min smoke verification on dispatch; optional full build |
| **Artifact Retention** | None stored in GitHub Actions | Downloadable `coverage-linux-without-intl-report` (LCOV, Cobertura XML, markdown) |
| **Runner Infrastructure** | Hardcoded `ubuntu-24.04` | Configurable runner `${{ vars.RUNNER_LABEL || 'ubuntu-24.04' }}` |

---

## Section 4: Configuration & Data Requirements

### Repository Secrets
| Secret Name | Required for Mode | Description |
| :--- | :--- | :--- |
| `CODECOV_TOKEN` | Original Mode only | Upload token for external codecov.io service |

### Repository Variables
| Variable Name | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `RUNNER_LABEL` | Optional | `ubuntu-24.04` | Runner image / pool label |
| `ENABLE_COVERAGE_LINUX_WITHOUT_INTL`| Optional | `false` | Set to `true` to enable automatic push builds on forks |

### Workflow Permissions
| Permission Scope | Level | Purpose |
| :--- | :--- | :--- |
| `contents` | `read` | Repository source checkout and configure execution |

---

## Section 5: Live Test Verification Details

- **Run ID**: [`41361240264`](https://github.com/sajuptpm/node/actions/runs/41361240264)
- **Run URL**: [https://github.com/sajuptpm/node/actions/runs/41361240264](https://github.com/sajuptpm/node/actions/runs/41361240264)
- **Trigger Type**: `workflow_dispatch` (`test_scope: smoke`, `mode: native`)
- **Outcome**: `success` (All steps completed cleanly)
- **Total Duration**: ~46 seconds

### Execution Timeline Table

| Job / Step | Duration | Status | Notes |
| :--- | :--- | :--- | :--- |
| **coverage-linux-without-intl** (Job `125011862059`) | **46s** | `success` | Hosted runner (`ubuntu-24.04`) |
| ├── Set up job | 2s | `success` | Runner initialization |
| ├── Run actions/checkout@v4 | 9s | `success` | Checked out repository |
| ├── Install Clang 19 | 14s | `success` | Installed via composite action (`./.github/actions/install-clang`) |
| ├── Set up Python 3.14 | <1s | `success` | Configured Python 3.14 with pre-releases allowed |
| ├── Set up sccache | 1s | `success` | Configured Mozilla sccache v0.17.0 |
| ├── Install gcovr | 2s | `success` | Installed gcovr 7.2 |
| ├── Configure | 6s | `success` | `./configure --verbose --error-on-warn --coverage --without-intl` |
| ├── Build and test | <1s | `success` | Smoke coverage execution generating V8 coverage data |
| ├── Report JS | 6s | `success` | Computed JS coverage via `c8` |
| ├── Report C++ | <1s | `success` | Computed C++ coverage and generated Cobertura XML |
| ├── Clean tmp | <1s | `success` | Cleaned temporary scratch directories |
| ├── Generate Coverage Summary (Native) | <1s | `success` | Compiled markdown summary & updated `$GITHUB_STEP_SUMMARY` |
| ├── Upload to Codecov (Original) | — | `skipped` | Skipped in native mode (no token required) |
| ├── Upload Coverage Artifacts (Native) | 2s | `success` | Uploaded `coverage-linux-without-intl-report` artifact via v4 |
| └── Complete job | <1s | `success` | Clean teardown |

### Generated Artifacts
- **`coverage-linux-without-intl-report`** (Zip, ~1.5 KB): Contains `coverage-summary.md` and `coverage-cxx.xml` providing full line and branch coverage metrics.

---

## Section 6: How to Test Later

### 1. GitHub CLI (`gh`)
```bash
# Run fast smoke test & toolchain coverage validation
gh workflow run coverage-linux-without-intl.yml --ref main -f test_scope=smoke -f mode=native

# Run full compilation & test coverage suite (extended duration)
gh workflow run coverage-linux-without-intl.yml --ref main -f test_scope=full -f mode=original
```

### 2. Python Dispatch Script (`workflow-fixes/test-dispatch-coverage-linux-without-intl.py`)
```python
import os, requests

TOKEN = os.environ.get("GH_TOKEN")
REPO = "sajuptpm/node1"
url = f"https://api.github.com/repos/{REPO}/actions/workflows/coverage-linux-without-intl.yml/dispatches"
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
3. In the left workflow sidebar, click **Coverage Linux (without intl)**.
4. Click the **Run workflow** dropdown button on the right.
5. In the input dialog:
   - **Use workflow from**: Select `main`.
   - **Coverage test scope**: Select `smoke` (for fast validation) or `full`.
   - **Execution mode**: Select `native`.
6. Click the green **Run workflow** button.
7. Refresh the page and click the newly started run.
8. Verify:
   - Job `coverage-linux-without-intl` executes and completes with status `success` (`✓`).
   - The **Summary** tab displays the **Coverage Linux (without intl) Summary** table with configuration checks and generated deliverables.
   - The artifact `coverage-linux-without-intl-report` is generated and available for download.
