# Bare-Metal Hardware Specifications for Running `benchmark/compare.js` and `benchmark.yml`

There is no hardcoded hardware check inside [`benchmark/compare.js`](file:///c:/projects/node/benchmark/compare.js), as required capacity depends on whether you are **only executing `compare.js` against pre-built binaries** or running the **full [`benchmark.yml`](file:///c:/projects/node/.github/workflows/benchmark.yml) workflow** (which compiles Node.js + V8 twice from C++ source before benchmarking).

Based on how [`benchmark/compare.js`](file:///c:/projects/node/benchmark/compare.js) and [`benchmark/cpu.sh`](file:///c:/projects/node/benchmark/cpu.sh) execute, here are the recommended bare-metal specifications.

---

## 1. Bare-Metal Hardware Specifications Matrix

| Hardware Resource | Minimum *(Running `compare.js` with pre-built binaries)* | Recommended Enterprise Spec *(Compiling Node.js + `benchmark.yml` + `compare.js`)* | Upstream `nodejs/build` Cluster Reality | Technical Rationale & Code Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **CPU** | **4 – 8 physical cores**<br>(x86_64 Intel/AMD or ARM64) | **16 – 32 physical cores**<br>(Intel Xeon Scalable / AMD EPYC / ARM64) | Enterprise **Intel Xeon** bare-metal servers (Equinix Metal / donated lab hosts) | • [`benchmark/compare.js`](file:///c:/projects/node/benchmark/compare.js#L110-L120) runs benchmarks **sequentially** (1 child process at a time), so microbenchmarks primarily use 1–4 cores.<br>• HTTP benchmarks (`wrk`, `autocannon`, `h2load`) run a load generator alongside the Node.js server—having 8–16+ cores lets you isolate them via `--set CPUSET=0-3` (`taskset`) while leaving spare cores for the OS.<br>• Compiling Node.js + V8 twice in `benchmark.yml` scales directly with core count. |
| **RAM** | **16 GB RAM** | **32 GB – 64 GB ECC RAM** | **64 GB – 256 GB+ ECC RAM** | • `compare.js` alone typically consumes < 4 GB (peaking around 4–8 GB on large `buffers` / `v8` / `streams` tests).<br>• Compiling Node.js + V8 + Perfetto in parallel (`make -j`) requires **16–32 GB+ RAM** to prevent OOM build failures. |
| **Storage (Disk)** | **50 GB SSD / NVMe** | **100 GB+ Enterprise NVMe SSD** | Enterprise SSD / NVMe | • Required for `fs` I/O benchmarks and storing two full Node.js git trees + compiled C++ build artifacts (`base_node`, `node`, and Nix store). |
| **Operating System** | **Ubuntu 24.04 LTS** (or 22.04 LTS) on bare metal | **Ubuntu 24.04 LTS** on bare metal *(root access)* | **Ubuntu LTS** managed via `nodejs/build` Ansible playbooks | • **Linux bare metal** is required to execute [`benchmark/cpu.sh`](file:///c:/projects/node/benchmark/cpu.sh#L3-L32) (`sudo ./benchmark/cpu.sh fast`), which locks `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` to `performance` (virtualized cloud VMs typically hide `cpufreq`).<br>• Required for Linux `taskset` CPU affinity pinning (`--set CPUSET=0`). |
| **Network** | Standard NIC (1 Gbps+) | Standard NIC (1 Gbps+) | Dedicated datacenter NIC | • HTTP/HTTP2 benchmarks run over `localhost` loopback, so external internet speed does not impact benchmark throughput. |

---

## 2. Required OS Tuning & Software Prerequisites on the Bare-Metal Host

From [`benchmark/cpu.sh`](file:///c:/projects/node/benchmark/cpu.sh) and [`doc/contributing/writing-and-running-benchmarks.md`](file:///c:/projects/node/doc/contributing/writing-and-running-benchmarks.md):
1. **CPU Governor Locked (`performance` mode)**: Run `sudo ./benchmark/cpu.sh fast` before benchmarking to eliminate CPU frequency scaling variance, and `sudo ./benchmark/cpu.sh reset` afterward.
2. **CPU Core Isolation (`taskset`)**: Pin benchmark processes to dedicated physical cores using `--set CPUSET=0` or `--set CPUSET=0-2`.
3. **Zero Concurrent Workloads**: Run only one benchmark job at a time (`concurrency: 1`) on the bare-metal server to avoid CPU contention.
4. **Benchmarker & Statistical Tools**: `wrk` or `autocannon` (`http`/`https`), `h2load` (`http2`), and either built-in `--analyze` or `R` (`ggplot2` + `plyr`) for [`benchmark/compare.R`](file:///c:/projects/node/benchmark/compare.R).

---

## 3. AWS `.metal` Instance Sizing vs. On-Premises Server Note

* **AWS EC2 `.metal` Instances**: AWS allocates the **entire physical server blade** for `.metal` instance types (`c7g.metal` = **64 vCPUs / 128 GiB RAM**; `c6i.metal` = **128 vCPUs / 256 GiB RAM**). While larger than `compare.js` strictly requires, launching `.metal` **on-demand for 30–60 minutes** costs only ~$1–$5 per run and eliminates hypervisor jitter.
* **On-Premises / Lab Bare-Metal Server**: A **16-core, 32–64 GB RAM, 100 GB NVMe Ubuntu 24.04 LTS** physical server is the optimal dedicated specification.
