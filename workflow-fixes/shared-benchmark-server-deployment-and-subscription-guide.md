# Node.js Benchmark Server: Deployment, Pipeline Usage, Subscriptions & AWS On-Demand Bare-Metal Guide

## 1. Reference Infrastructure Item

| Field | Value |
| :--- | :--- |
| **Tool / Infra Name** | Shared physical/VM benchmark server |
| **Category** | Infra (Test / Performance Quality Gate) |
| **Specification** | Dedicated Ubuntu 24.04 LTS Bare-Metal Performance Server |
| **Purpose** | Runs Node.js microbenchmarks and HTTP throughput tests (`benchmark.yml`) without virtualization jitter or noisy neighbors. |
| **Vendor (Listed)** | Microsoft / GitHub (or Cloud / On-Premises Bare-Metal Provider) |
| **Record Type** | Upstream Original Tool |
| **License** | Hardware / Cloud Infrastructure EULA |
| **Cost Baseline** | Standard Metered PAYG (Dedicated Bare-Metal Server @ ~$250/mo = $3,000/yr) |
| **Upstream Reference** | [https://github.com/nodejs/benchmarking](https://github.com/nodejs/benchmarking) |
| **Component** | Node.js 26.13.0 |
| **Cost Classification** | Paid |

---

## 2. Where Is This Used?

This infrastructure serves as the **deterministic performance execution host** to measure Node.js microbenchmarks (`benchmark/compare.js`) and HTTP/HTTPS/HTTP2 throughput (`wrk`, `autocannon`, `h2load`) without cloud virtualization jitter or noisy-neighbor CPU contention.

### Why Upstream Requires Dedicated Hardware
* Standard cloud virtual machines (including default GitHub-hosted runners) share underlying physical CPU sockets with other tenants and dynamically scale CPU clock speeds, causing **2%–5% measurement jitter**.
* Because microbenchmarks are sensitive to nanosecond/microsecond timing differences, the **Node.js Benchmarking Working Group** ([`nodejs/benchmarking`](https://github.com/nodejs/benchmarking)) executes authoritative release performance tests on **dedicated physical bare-metal servers** (donated hardware attached to the OpenJS Jenkins CI farm) with CPU frequency scaling disabled (`performance` governor).
* Upstream [`benchmark.yml`](file:///c:/projects/node/.github/workflows/benchmark.yml) explicitly prints a warning in every GitHub Actions summary:
  > *"Do not take GHA benchmark results as face value, always confirm them using a dedicated machine, e.g. Jenkins CI."*

---

## 3. Which Pipeline Uses It?

1. **GitHub Actions Pipeline**: **`Benchmark`** — [`.github/workflows/benchmark.yml`](file:///c:/projects/node/.github/workflows/benchmark.yml)
   * **Trigger**: Manual dispatch (`workflow_dispatch`).
   * **Execution**: In upstream `nodejs/node`, it compiles both the base commit and target PR commit via Nix (`tools/nix/pkgs.nix`), executes [`benchmark/compare.js`](file:///c:/projects/node/benchmark/compare.js) across categories (`http`, `buffers`, `crypto`, `misc`, etc.), and runs statistical Welch's t-tests via [`benchmark/compare.R`](file:///c:/projects/node/benchmark/compare.R).
2. **Upstream Jenkins CI Pipeline**: Node.js Benchmarking CI on **`ci.nodejs.org`**, documented in [`doc/contributing/writing-and-running-benchmarks.md`](file:///c:/projects/node/doc/contributing/writing-and-running-benchmarks.md#L763-L767) and [`nodejs/benchmarking/docs/core_benchmarks.md`](https://github.com/nodejs/benchmarking/blob/HEAD/docs/core_benchmarks.md).

---

## 4. Where Do You Need to Create This Server?

Because upstream's donated bare-metal lab is private to the Node.js Benchmarking Working Group, your enterprise fork has **three deployment locations** depending on jitter tolerance and operational overhead:

### Option A: Inside Your Own On-Premises Lab / Corporate Data Center *(Best Value if Hardware Exists)*
* **Where**: Provision a dedicated physical 1U server or an isolated physical partition/host in your internal engineering lab running **Ubuntu 24.04 LTS**.
* **How to connect**: Install the free **GitHub Self-Hosted Runner** (`actions/runner`) directly on bare metal, lock the CPU governor (`cpupower frequency-set -g performance`), tag it (e.g., `benchmark-baremetal`), and target it via `runs-on:` in `benchmark.yml`.
* **Benefit**: True **0% hypervisor jitter** and full hardware `perf` counter access.

### Option B: In Your Enterprise Cloud Account (AWS EC2, Microsoft Azure, Equinix Metal, Hetzner)
* **Where**: Launch an **on-demand bare-metal or dedicated compute instance** (Ubuntu 24.04 LTS) inside your AWS or Azure account.
* **How to connect**: Register it as an **ephemeral GitHub Self-Hosted Runner**—provision it automatically only when `benchmark.yml` runs, execute tests (~30–60 minutes), and terminate/stop it immediately after.
* **Cost Guardrail**: Never leave a cloud bare-metal server running 24×7×365 (~$3,000–$47,000/yr). Running strictly on demand for 2–10 benchmark runs/month reduces cloud cost to **~$40–$278/year**.

### Option C: Directly Inside GitHub Organization Settings *(Zero Server Maintenance)*
* **Where**: Navigate to **GitHub Organization / Enterprise Settings → Actions → Runners → New larger runner**.
* **How to connect**: Provision a managed Ubuntu 24.04 **GitHub Larger Runner** (8-core / 32 GB RAM or 16-core / 64 GB RAM). GitHub runs it on Microsoft Azure compute and bills strictly per minute.
* **Benefit**: Zero server setup, OS patching, or SSH keys. Minor ~2–5% VM jitter is mitigated by setting `runs: 30` for statistical significance.

---

## 5. Which Subscription Do You Need to Buy for Your Enterprise?

Although the reference sheet lists `Microsoft / GitHub` alongside `~$250/mo = $3,000/yr`, **Microsoft/GitHub does not offer a flat "$250/mo bare-metal runner subscription"**. Instead, purchase depends on which deployment option you choose:

| Deployment Choice | Required Vendor & Subscription / Plan | Billing Model & Cost Estimate | Enterprise Procurement Notes |
| :--- | :--- | :--- | :--- |
| **1. GitHub Larger Runners** *(100% GitHub-managed on Azure)* | **GitHub Team** ($4/user/mo) or **GitHub Enterprise Cloud** ($21/user/mo) + **GitHub Actions Metered Billing (PAYG)** | **Per-minute only** (no idle fee):<br>• 8-Core Linux: **$0.022/min**<br>• 16-Core Linux: **$0.042/min**<br>*(~$20 – $176/yr for 2–10 runs/mo)* | Larger Runners are **unavailable on GitHub Free** and are never free even on public repositories; a paid GitHub Team or Enterprise Cloud plan is mandatory. |
| **2. Cloud Self-Hosted Server** *(AWS / Azure / Bare-Metal Host)* | **AWS Account** or **Microsoft Azure PAYG / Enterprise Agreement** *(or Equinix / Hetzner)* | • **Always-on 24×7**: ~$150 – $500/mo (**$1,800 – $6,000/yr** — matches your baseline).<br>• **On-Demand / Ephemeral**: **~$8 – $278/yr** depending on VM vs. `.metal`. | Use ephemeral provisioning (Terraform / GitHub Action startup step) to avoid paying for idle 24×7 compute. |
| **3. On-Premises Physical Server** *(Internal lab / shared Proxmox host)* | **No new cloud subscription required** *(uses existing corporate hardware + current GitHub plan)* | **$0/yr incremental software cost** *(only internal power/hardware allocation if shared; ~$1,433–$2,700/yr if buying a dedicated 1U server)*. | Detailed financial breakdown available in [`workflow-fixes/benchmark-runner-alternatives-and-cost-analysis.md`](file:///c:/projects/node/workflow-fixes/benchmark-runner-alternatives-and-cost-analysis.md). |

---

## 6. Creating a Dedicated On-Demand Bare-Metal Server in AWS

**Yes, you can create a dedicated On-Demand Bare-Metal server in AWS** with **zero long-term contract** and **per-second billing**.

### How AWS On-Demand Bare-Metal Works
* AWS provides **`.metal` instance types** powered by the **AWS Nitro System**.
* Your Ubuntu 24.04 OS runs directly on physical CPU silicon and memory **without any hypervisor**, giving you **0% virtualization jitter** and direct access to hardware performance counters (`perf`)—identical to an on-premises physical server.
* **Per-Second Billing**: Under AWS On-Demand pricing, Linux `.metal` instances are billed **per second** (with a 60-second minimum). You pay **$0** once terminated (or stop paying compute charges when stopped, paying only a few cents/day for the EBS storage disk).
* **Important Operational Notes**:
  * Bare-metal instances take slightly longer to initialize (~5–15 minutes) than standard virtualized EC2 instances because physical host hardware must boot.
  * Instance hibernation is not supported on bare-metal instance types.

### Recommended AWS `.metal` Instance Types for Node.js Benchmarking
* **AWS Graviton3 ARM64 Bare Metal**: `c7g.metal` (64 vCPUs, 128 GiB RAM) — highest cost-efficiency for bare-metal benchmarking.
* **3rd Gen Intel Xeon Bare Metal**: `c6i.metal` (128 vCPUs, 256 GiB RAM) — x86_64 physical silicon.
* **4th Gen Intel Xeon Bare Metal**: `c7i.metal-24xl` (96 vCPUs, 192 GiB RAM) and `c7i.metal-48xl` (192 vCPUs, 384 GiB RAM).

### Official AWS Links & Documentation
* **Amazon EC2 On-Demand Pricing** *(filter by Region & `.metal` instance)*: [https://aws.amazon.com/ec2/pricing/on-demand/](https://aws.amazon.com/ec2/pricing/on-demand/)
* **Amazon EC2 On-Demand Instances Documentation**: [https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-on-demand-instances.html](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-on-demand-instances.html)
* **Amazon EC2 Instance Types Guide** *(Bare Metal architecture & Nitro details)*: [https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html)
* **C7i Bare Metal (`c7i.metal-24xl` / `c7i.metal-48xl`)**: [https://aws.amazon.com/ec2/instance-types/c7i/](https://aws.amazon.com/ec2/instance-types/c7i/)
* **C6i Bare Metal (`c6i.metal`)**: [https://aws.amazon.com/ec2/instance-types/c6i/](https://aws.amazon.com/ec2/instance-types/c6i/)
* **C7g Bare Metal (`c7g.metal`)**: [https://aws.amazon.com/ec2/instance-types/c7g/](https://aws.amazon.com/ec2/instance-types/c7g/)
