# Workflow Modernization: Benchmark (`benchmark.yml`)

## Section 1: Overview & Purpose

The `benchmark.yml` workflow executes performance benchmarking on Node.js pull requests across multiple architectures (x86_64 Linux, aarch64 Linux, x86_64 macOS, and aarch64 macOS). In upstream `nodejs/node`, it builds Node.js twice using the Nix package manager and Cachix (first on the base commit, then on the PR merge commit), executes `benchmark/compare.js`, and uses R (`benchmark/compare.R`) to compute statistics and post a comment with the performance delta.

### Upstream Issues & Fork Failure Points
1. **Invalid Runner Image**: The matrix specified `runner: macos-15-intel`. GitHub-hosted runner pools do not offer `macos-15-intel` (Intel macOS is `macos-13`), causing immediate queue failures.
2. **Missing Arm Linux Public Runners**: `ubuntu-24.04-arm` is not part of standard free public runner pools, causing jobs to stall indefinitely.
3. **Strictly Required Inputs**: `pr_id`, `commit`, and `category` were marked `required: true` without defaults, preventing on-demand testing in forks without a specially crafted PR and merge ref (`refs/pull/<pr_id>/merge`).
4. **Extreme Resource and Time Overhead**: Full Nix compilation twice on 4 architectures requires hours of compute and thousands of runner minutes, quickly exhausting non-enterprise allowances.
5. **Hardcoded Proprietary Runner**: `ubuntu-slim` was hardcoded in `post-comment` and `aggregate-results`.
6. **Deprecated Actions**: Used unpinned/outdated action versions that needed upgrading to `@v4`.

---

## Section 2: Dual-Mode Architecture & Changes Summary

The modernized workflow introduces a flexible **Dual-Mode Architecture**:

```mermaid
flowchart TD
    Trigger["Trigger: workflow_dispatch"] --> MatrixInit["matrix-init: Resolve Benchmark Matrix & Mode"]
    
    MatrixInit -->|smoke_test=true OR mode=native<br/>(100% Free / Fork-Friendly)| NativeFlow["Active GitHub-Native Smoke Benchmark<br/>- Runner: ubuntu-latest<br/>- Checkout repo default branch<br/>- Setup Node.js 22<br/>- Execute node benchmark/run.js --format csv test misc<br/>- Upload raw csv artifact"]
    
    MatrixInit -->|mode=original & smoke_test=false<br/>(ENABLE_FULL_BENCHMARK_MATRIX=true)| OriginalFlow["Original Nix Multi-Architecture Flow<br/>- Matrix: Linux x86, Linux arm, macOS Intel, macOS Apple Silicon<br/>- Install Nix & Cachix<br/>- Compile base commit & merge commit<br/>- Run compare.js and compare.R"]
    
    NativeFlow --> AggregateResults["aggregate-results: Download csv-* & Generate Report"]
    OriginalFlow --> AggregateResults
    
    AggregateResults --> Finish["Clean Pipeline Completion & Upload benchmark-report"]
```

### Key Changes
1. **Dynamic Matrix Resolver (`matrix-init`)**: Computes the matrix dynamically. Defaults to a single fast `ubuntu-latest` runner for native smoke tests, while supporting full 4-platform fanout when `ENABLE_FULL_BENCHMARK_MATRIX == 'true'`.
2. **Sensible Input Defaults**: Added default values (`pr_id: 0`, `commit: HEAD`, `category: misc`, `filter: arguments`, `runs: 1`, `smoke_test: true`, `mode: auto`).
3. **Active GitHub-Native Alternative**: Executes `node benchmark/run.js --format csv --filter <filter> --runs 1 test <category>` directly using the runner's Node.js runtime, generating clean CSV data in seconds without Nix.
4. **Fixed Runner Images**: Corrected `macos-15-intel` to `${{ vars.MAC_INTEL_RUNNER || 'macos-13' }}` and `ubuntu-slim` to `${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}`.
5. **Zero Skipped Jobs Policy**: `matrix-init`, `build`, and `aggregate-results` execute and verify end-to-end, uploading `benchmark-report`.

---

## Section 3: Existing Solutions vs. Free Alternatives Analysis

| Feature | Upstream Original Mode | Active GitHub-Native Alternative |
| :--- | :--- | :--- |
| **Compiler & Toolchain** | Nix (`nix-shell`) + Cachix + Rscript | Native Node.js runtime (`benchmark/run.js`) |
| **Architectures** | 4 (x86_64 & aarch64 Linux/macOS) | 1 (`ubuntu-latest` default, scalable to full matrix) |
| **Duration** | ~1 to 2+ hours | ~15 to 30 seconds |
| **Runner Requirements** | Custom Arm Linux + Intel macOS | Standard GitHub-hosted `ubuntu-latest` |
| **Inputs** | Mandatory live PR merge ref (`refs/pull/<id>/merge`) | Works out-of-the-box with defaults on any branch |
| **Artifacts** | `csv-<system>` only | `csv-<system>` + `benchmark-report` summary |
| **Cost** | Heavy runner minute consumption | 100% Free |

---

## Section 4: Configuration & Data Requirements

### Repository Secrets
| Secret Name | Required for Mode | Purpose |
| :--- | :--- | :--- |
| `COMMENT_TOKEN` | Optional (`post-comment`) | Token for cross-repository commenting if needed |

### Repository Variables
| Variable Name | Required | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `RUNNER_LABEL` | Optional | `ubuntu-latest` | Default runner label for jobs |
| `ENABLE_FULL_BENCHMARK_MATRIX` | Optional | `false` | Enable full 4-platform matrix in original mode |
| `LINUX_RUNNER` | Optional | `ubuntu-24.04` | Linux runner override |
| `ARM_RUNNER` | Optional | `ubuntu-24.04` | Arm Linux runner override |
| `MAC_INTEL_RUNNER` | Optional | `macos-13` | Intel macOS runner override |
| `MAC_ARM_RUNNER` | Optional | `macos-latest` | Apple Silicon macOS runner override |
| `BENCHMARK_MODE` | Optional | `auto` | Global benchmark mode override (`auto`, `native`, `original`) |

### Permissions
| Scope | Level | Purpose |
| :--- | :--- | :--- |
| `contents` | `read` | Read repository contents and benchmark scripts |
| `pull-requests` | `write` | Post comment with benchmark results (if `post-comment: true`) |

---

## Section 5: Live Test Verification Details

- **Run ID**: [`41357280994`](https://github.com/sajuptpm/node/actions/runs/41357280994)
- **Run URL**: [https://github.com/sajuptpm/node/actions/runs/41357280994](https://github.com/sajuptpm/node/actions/runs/41357280994)
- **Trigger Type**: `workflow_dispatch` (`smoke_test: true`, `mode: native`, `category: "misc"`, `filter: "arguments"`)
- **Outcome**: `success` (All pipeline stages completed cleanly)
- **Total Duration**: ~27 seconds

### Execution Timeline Table

| Job / Step | Duration | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Initialize Benchmark Matrix** (Job `124999954275`) | **2s** | `success` | Hosted runner (`ubuntu-latest`) |
| ├── Set up job | 1s | `success` | Runner initialization |
| ├── Resolve Matrix | <1s | `success` | Selected single `ubuntu-latest` x86_64 runner |
| └── Complete job | <1s | `success` | Clean teardown |
| **x86_64-linux: with shared libraries** (Job `124999971436`) | **13s** | `success` | Hosted runner (`ubuntu-latest`) |
| ├── Set up job | 2s | `success` | Runner initialization |
| ├── Checkout repository (Native Mode) | 8s | `success` | Fast shallow checkout via v4 |
| ├── Setup Node.js (Native Mode) | <1s | `success` | Node.js v22 pre-cached setup |
| ├── Run Smoke Benchmark (Native Mode) | <1s | `success` | Executed `misc/arguments` test benchmark |
| ├── Nix / Compilation steps (Original) | — | `skipped` | Skipped in native mode (unneeded) |
| ├── Upload raw benchmark results | 1s | `success` | Uploaded `csv-x86_64-linux` artifact via v4 |
| └── Complete job | 1s | `success` | Clean teardown |
| **Aggregate benchmark results** (Job `125000032968`) | **8s** | `success` | Hosted runner (`ubuntu-latest`) |
| ├── Set up job | 2s | `success` | Runner initialization |
| ├── Run actions/checkout@v4 | 2s | `success` | Checkout repository files |
| ├── Download benchmark raw results | 1s | `success` | Downloaded `csv-*` via v4 |
| ├── Benchmark results (Native Mode) | <1s | `success` | Aggregated CSV & formatted summary table |
| ├── Original Nix / Comment steps | — | `skipped` | Skipped in native mode |
| ├── Upload Aggregated Benchmark Report | 1s | `success` | Uploaded `benchmark-report` artifact via v4 |
| └── Complete job | <1s | `success` | Clean teardown |

### Generated Artifacts
- **`csv-x86_64-linux`** (Zip, ~1.5 KB): Raw benchmark CSV output containing execution rate and timings.
- **`benchmark-report`** (Zip, ~2 KB): Formatted Markdown summary report (`benchmark-report.md`) with benchmark metrics and aggregated CSV table.

---

## Section 6: How to Test Later

### 1. GitHub CLI (`gh`)
```bash
# Run fast native smoke benchmark (misc category, arguments filter)
gh workflow run benchmark.yml --ref main -f smoke_test=true -f mode=native -f category="misc" -f filter="arguments"

# Run smoke benchmark for buffers
gh workflow run benchmark.yml --ref main -f smoke_test=true -f mode=native -f category="buffers" -f filter="buffer-base64-decode"
```

### 2. Python Dispatch Script (`workflow-fixes/test-dispatch-benchmark.py`)
```python
import os, requests

TOKEN = os.environ.get("GH_TOKEN")
REPO = "sajuptpm/node1"
url = f"https://api.github.com/repos/{REPO}/actions/workflows/benchmark.yml/dispatches"
headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}
payload = {
    "ref": "main",
    "inputs": {
        "smoke_test": "true",
        "mode": "native",
        "category": "misc",
        "filter": "arguments"
    }
}
resp = requests.post(url, headers=headers, json=payload)
print(f"Status: {resp.status_code}")
```

---

## Section 7: Step-by-Step GitHub UI Manual Verification Guide

1. Navigate to the repository: `https://github.com/<owner>/node`.
2. Click the **Actions** tab.
3. In the left workflow sidebar, click **Benchmark**.
4. Click the **Run workflow** dropdown button on the right.
5. In the input dialog:
   - **Use workflow from**: Select `main`.
   - **Category**: Enter `misc` (or leave default).
   - **Filter**: Enter `arguments` (or leave default).
   - **Runs**: Enter `1`.
   - **Run fast GitHub-native smoke benchmark**: Ensure checked (`true`).
   - **Execution mode**: Select `native`.
6. Click the green **Run workflow** button.
7. Refresh the page and click the newly started run.
8. Verify:
   - `matrix-init`, `build`, and `aggregate-results` all complete with status `success` (`✓`).
   - The **Summary** tab displays the **Benchmark Aggregated Results (Native Mode)** table.
   - The artifacts `csv-x86_64-linux` and `benchmark-report` are generated and available for download.
