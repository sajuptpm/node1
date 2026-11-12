# Is a GitHub Machine User Required in This Repository?

## 1. Direct Answer

**No — a GitHub Machine User is NOT required in this repository.**

While upstream `nodejs/node` relies on a dedicated Machine User (`nodejs-github-bot`, `secrets.GH_USER_TOKEN`) across 14 workflows, an enterprise fork can run these workflows cleanly without creating or paying for a Machine User seat.

---

## 2. Why Upstream `nodejs/node` Uses a Machine User

Upstream uses `nodejs-github-bot` (`secrets.GH_USER_TOKEN`) across workflows such as [`create-release-proposal.yml`](file:///c:/projects/node/.github/workflows/create-release-proposal.yml), `commit-queue.yml`, `label-pr.yml`, `update-v8.yml`, and `update-openssl.yml` for two reasons:
1. **Triggering Downstream CI on Automated PRs**: Commits pushed or Pull Requests created using GitHub's built-in `GITHUB_TOKEN` **do not trigger downstream CI workflows** (`on: pull_request`, `on: push`) by design to prevent infinite recursion loops. Upstream explicitly notes in `create-release-proposal.yml`:
   > `# We want the bot to push the release commit so CI runs on it.`
2. **Legacy Historical Architecture**: `nodejs-github-bot` was established years before modern **GitHub Apps** and `actions/create-github-app-token` became the recommended GitHub standard.

---

## 3. How This Repo Works Without a Machine User

| Requirement in This Repository | Upstream Legacy: **Machine User (`GH_USER_TOKEN`)** | Recommended Enterprise Option: **Internal GitHub App** | Simple Fork Default: **Built-in `GITHUB_TOKEN`** |
| :--- | :--- | :--- | :--- |
| **Labeling, commenting, & triage** (`label-pr.yml`, `contributor-guidance.yml`, `nix-changes-comment.yml`) | Supported (`GH_USER_TOKEN`) | **Supported ($0)** | **Supported ($0)** *(with `pull-requests: write` / `issues: write`)* |
| **Release proposals & dependency PRs** (`create-release-proposal.yml`, `update-v8.yml`, `update-openssl.yml`) | Supported (`GH_USER_TOKEN`) | **Supported ($0)** | **Supported ($0)** *(with `contents: write`, `pull-requests: write`)* |
| **Auto-triggering CI on bot-opened PRs** | Yes | **Yes** | No *(requires human close/reopen or manual `workflow_dispatch`)* |
| **Auto-merging PRs / bypassing branch protection** (`commit-queue.yml`) | Yes | **Yes** *(add GitHub App to branch protection bypass list)* | Restricted on protected branches |
| **Node.js Foundation governance workflows** (`find-inactive-collaborators.yml`, `find-inactive-tsc.yml`) | Runs only on `nodejs/node` | **Not needed** in a company fork | **Not needed** in a company fork |
| **Credential Security** | Long-lived PAT (`GH_USER_TOKEN`) | **Short-lived 1-hour installation token** | Short-lived per-job token |
| **Paid GitHub User Seat Required?** | **Yes** (1 paid seat on Team/Enterprise private orgs) | **No ($0.00)** — GitHub Apps consume 0 seats | **No ($0.00)** |

---

## 4. Conclusion

* **Is a Machine User required?** **No.**
* **For simple fork testing & execution**: Built-in **`GITHUB_TOKEN`** is sufficient and already verified in [`workflow-fixes/create-release-proposal.md`](file:///c:/projects/node/workflow-fixes/create-release-proposal.md).
* **For full upstream parity (auto-triggering CI on automated PRs & bypassing branch protection)**: Deploy an **internal GitHub App** (`actions/create-github-app-token`) at **$0.00/year** in seat licensing costs.
