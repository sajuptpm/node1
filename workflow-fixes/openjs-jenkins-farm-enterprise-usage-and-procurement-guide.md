# OpenJS Jenkins Build Farm (`ci.nodejs.org`): Enterprise Usage, Subscription & Procurement Guide

## 1. Reference Infrastructure Item

| Field | Value |
| :--- | :--- |
| **Tool / Infra Name** | OpenJS Jenkins Build Farm upstream |
| **Category** | Infra (Cross-Platform Build & Regression CI) |
| **Product / Version** | Jenkins LTS (`ci.nodejs.org`) |
| **Purpose** | Orchestrates remote cross-platform build and regression test matrix for Auto Start CI (`auto-start-ci.yml`) via `ci.nodejs.org`. |
| **Vendor / Operator** | OpenJS Foundation |
| **Record Type** | Upstream Original Tool |
| **License** | MIT License (Jenkins Core) + Foundation Infrastructure |
| **Subscription / Infra Model** | Enterprise Cloud VM Pool (Vendor Quote Required for Dedicated Cloud Farm) |
| **Upstream URL** | [https://ci.nodejs.org/](https://ci.nodejs.org/) |
| **Component** | Node.js 26.13.0 |
| **Cost Classification** | Free (Open-Source Jenkins + Donated Corporate Hardware) |

---

## 2. Where Is This Used?

In upstream `nodejs/node`, `ci.nodejs.org` is used as the external build and test orchestrator across **two active GitHub Actions workflows** (and referenced in two additional upstream workflows):

1. **`Auto Start CI`** ([`.github/workflows/auto-start-ci.yml`](file:///c:/projects/node/.github/workflows/auto-start-ci.yml)):
   * Runs every 5 minutes (`cron`), executing [`tools/actions/start-ci.sh`](file:///c:/projects/node/tools/actions/start-ci.sh) and `@node-core/utils` (`ncu-ci available`, `ncu-ci workload`, `ncu-ci run`).
   * Uses `JENKINS_USER` and `JENKINS_TOKEN` secrets to dispatch full cross-platform builds (`node-test-pull-request`) on `https://ci.nodejs.org/`.
2. **`Commit Queue`** ([`.github/workflows/commit-queue.yml`](file:///c:/projects/node/.github/workflows/commit-queue.yml)):
   * Uses `JENKINS_USER` and `JENKINS_TOKEN` via `ncu-ci` to verify that all required Jenkins CI jobs passed before auto-merging approved PRs into `nodejs/node`.
3. **Secondary / Advisory Upstream References**:
   * [`benchmark.yml`](file:///c:/projects/node/.github/workflows/benchmark.yml): Prints an advisory warning instructing maintainers to confirm GitHub Actions benchmark results on a dedicated machine (*"e.g. Jenkins CI"*).
   * Upstream `update-wpt.yml` & `contributor-guidance.yml`: Referenced `JENKINS_USER` / Jenkins CI checks in PR triage and WPT update workflows.

### Platforms & Tests Executed by Upstream Jenkins
* **Standard OS Platforms**: Linux (Ubuntu/RHEL/Alpine), Windows, macOS.
* **Special / Exotic Enterprise Platforms**: IBM AIX (`ppc64`), IBM z/OS (`s390x`), PowerPC (`ppc64le`), SmartOS, FreeBSD, Raspberry Pi / ARM.
* **Test Suites**: Full Node.js C++ build + regression suite (`make test` / `vcbuild.bat test`).

---

## 3. How Can I Use It in My Enterprise?

You **cannot** connect an enterprise fork directly to upstream's `https://ci.nodejs.org/` controller, because it is private OpenJS Foundation infrastructure restricted to Node.js collaborators with confidential `JENKINS_TOKEN` credentials.

In an enterprise fork, you have **two practical implementation paths**:

### Option A: Replace Jenkins with Native GitHub Actions Runners *(Recommended for Standard Platforms)*
* If your enterprise only targets **Linux (x64 / ARM64), Windows, and macOS**, you do **not** need Jenkins at all.
* Run the exact same build and regression tests (`./configure && make -j4 && make test-only` on Linux/macOS, `vcbuild.bat test` on Windows) directly inside GitHub Actions using standard hosted runners (`ubuntu-latest`, `ubuntu-24.04-arm`, `windows-latest`, `macos-latest`) or **GitHub Self-Hosted Runners** attached to your enterprise lab/cloud VMs.
* Detailed test mappings and runner commands are documented in:
  * [`workflow-fixes/jenkins-ci-pipeline-tests-and-runner-migration.md`](file:///c:/projects/node/workflow-fixes/jenkins-ci-pipeline-tests-and-runner-migration.md)
  * [`workflow-fixes/auto-start-ci-upstream-and-runner-analysis.md`](file:///c:/projects/node/workflow-fixes/auto-start-ci-upstream-and-runner-analysis.md)

### Option B: Deploy Your Own Private Jenkins LTS Controller *(Recommended if Supporting Rare/Custom Hardware)*
* Deploy **Jenkins LTS** (100% free Docker container `jenkins/jenkins:lts` or Linux VM) inside your corporate network or enterprise cloud.
* Connect your enterprise worker agents (Linux, Windows, macOS, or proprietary AIX / PowerPC / z/OS hosts) using the open-source pipeline definitions from [`nodejs/build/jenkins/pipelines`](https://github.com/nodejs/build/tree/main/jenkins/pipelines).
* Configure your repository secrets (`JENKINS_USER`, `JENKINS_TOKEN`) and point `ncu-ci` / `start-ci.sh` to your internal Jenkins server URL instead of `ci.nodejs.org`.

---

## 4. Should I Buy Any Subscription?

* **For Jenkins Software: NO ($0.00 / year).**
  * Jenkins LTS is 100% free and open-source software under the **MIT License**. There are no per-user seat fees, agent limits, or commercial subscriptions required to run Jenkins.
* **For Compute / Worker Infrastructure**:
  * **Standard OS targets (Linux / Windows / ARM64 / macOS)**: **$0 software subscription** when using free public GitHub Actions runners, existing included GitHub Team/Enterprise minutes, or existing internal corporate VMs/lab servers.
  * **Exotic / Proprietary OS targets (IBM AIX, IBM z/OS mainframes)**: **Cloud / Hardware Purchase Required** *only* if a customer contractually mandates support for those architectures (e.g., renting **IBM Power Virtual Server** / IBM Z cloud capacity, or using customer-supplied hardware). That conditional mainframe/VM reserve is why the spreadsheet notes *"Vendor Quote Required for Dedicated Cloud Farm"*.
  * *(Optional Enterprise SLA)*: Only if corporate IT policy explicitly mandates a **paid commercial vendor support contract** for Jenkins would you purchase **CloudBees CI**—otherwise community **Jenkins LTS** is completely free.

---

## 5. Can I Purchase the Same Product?

* **You cannot purchase access to `ci.nodejs.org`**:
  * The *"OpenJS Jenkins Build Farm"* is not a commercial SaaS product for sale—it is a private community cluster operated by the Node.js Build Working Group on hardware donated in-kind by corporate sponsors (**DigitalOcean, IBM, Equinix Metal, Arm, MacStadium, and Microsoft Azure**).
* **You CAN obtain the exact same underlying product for free**:
  * **Orchestrator Software**: **Jenkins LTS** ([https://www.jenkins.io/](https://www.jenkins.io/)) — free, open-source, MIT License.
  * **Build & Pipeline Scripts**: **Node.js Build WG Repository** ([https://github.com/nodejs/build](https://github.com/nodejs/build)) — open-source Ansible playbooks, container definitions, and Jenkinsfiles used to operate `ci.nodejs.org`.
  * **Commercial Supported Equivalent (Optional)**: **CloudBees CI** ([https://www.cloudbees.com/products/cloudbees-ci](https://www.cloudbees.com/products/cloudbees-ci)) offers enterprise-supported Jenkins with commercial SLAs if required by procurement policy.
