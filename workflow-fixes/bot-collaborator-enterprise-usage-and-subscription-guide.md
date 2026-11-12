# Bot Collaborator (`node-bot` / `GH_USER_TOKEN`): Purpose, Enterprise Usage & Subscription Guide

## 1. Reference Tool / Infrastructure Item

| Field | Value |
| :--- | :--- |
| **Tool / Infra Name** | `bot collaborator upstream` |
| **Category** | Tool (Git & Release Automation Identity) |
| **Product / Version** | `node-bot` GitHub App / Dedicated Committer PAT v2 (`nodejs-github-bot`) |
| **Purpose** | Performs automated Git commits, branch rebases, PR creation, auto-merging, and release proposal automation across `create-release-proposal.yml` and companion workflows. |
| **Vendor** | Microsoft / GitHub |
| **Record Type** | Upstream Original Tool |
| **License** | GitHub Terms of Service |
| **Subscription Model** | Team Plan (Free Automation Account via GitHub App / $4/user/mo per seat on Team Tier) |
| **Official Site** | [https://github.com](https://github.com) |
| **Component** | Node.js 26.13.0 |
| **Cost Classification** | Paid *(if deployed as a Machine User seat in a private org)* / Free *(if deployed as a GitHub App or `GITHUB_TOKEN`)* |

---

## 2. What Is This?

In upstream `nodejs/node`, this refers to the **automated bot collaborator identity** (**`nodejs-github-bot`**, Git author `"Node.js GitHub Bot" <github-bot@iojs.org>`), authenticated via the repository secret **`secrets.GH_USER_TOKEN`**.

### Why Upstream Uses a Separate Bot Token Instead of Built-in `GITHUB_TOKEN`
* By GitHub Actions security design, commits pushed or Pull Requests opened using the default `${{ secrets.GITHUB_TOKEN }}` **do not trigger downstream CI workflows** (`on: push`, `on: pull_request`), in order to prevent infinite workflow loops.
* As explicitly commented in upstream [`.github/workflows/create-release-proposal.yml`](file:///c:/projects/node/.github/workflows/create-release-proposal.yml):
  > `# We want the bot to push the release commit so CI runs on it.`
* Using `secrets.GH_USER_TOKEN` enables automated workflows to push release commits, open PRs, auto-merge approved PRs, apply collaborator labels, and **automatically trigger CI workflows** on those PRs/commits.

### Where It Is Used in Upstream (`nodejs/node`)
In upstream `nodejs/node`, `secrets.GH_USER_TOKEN` is referenced across **14 workflows**:
* **Release & Commit Automation**: `create-release-proposal.yml`, `commit-queue.yml`, `post-release.yml`, `tools.yml`
* **Dependency & Data Updates**: `update-v8.yml`, `update-openssl.yml`, `update-wpt.yml`, `timezone-update.yml`
* **PR Hygiene & Governance**: `contributor-guidance.yml`, `find-inactive-collaborators.yml`, `find-inactive-tsc.yml`, `label-pr.yml`, `linters.yml`, `nix-changes-comment.yml`

---

## 3. How Can I Use It in My Enterprise?

Upstream's `GH_USER_TOKEN` is private to the Node.js Technical Steering Committee / Release Team. In your enterprise fork, you have **three implementation options**:

### Option A: Create an Internal GitHub App *(Recommended Enterprise Standard — $0)*
1. Go to **GitHub Organization Settings → Developer settings → GitHub Apps → New GitHub App**.
2. Grant repository permissions: `Contents: Read & Write`, `Pull requests: Read & Write`, and `Issues: Read & Write`.
3. Install the App on your forked `node` repository, generate a Private Key, and store `BOT_APP_ID` and `BOT_APP_PRIVATE_KEY` as GitHub Actions secrets.
4. Add an `actions/create-github-app-token` step at the start of `create-release-proposal.yml` (and related workflows) to generate a short-lived installation token (`steps.app-token.outputs.token`) passed into `BOT_TOKEN` / `GH_USER_TOKEN`.
* **Advantages**: Automatically triggers downstream CI on automated PRs (solving the `GITHUB_TOKEN` limitation), auto-expires tokens every 60 minutes (strong security posture), and **consumes ZERO paid user seats**.

### Option B: Fallback to Built-in `GITHUB_TOKEN` *(Zero Setup — $0)*
* Configure the workflow to fall back to `${{ secrets.GH_USER_TOKEN || secrets.GITHUB_TOKEN }}` (as documented in [`workflow-fixes/create-release-proposal.md`](file:///c:/projects/node/workflow-fixes/create-release-proposal.md)).
* **Trade-off**: Automated PRs opened with `GITHUB_TOKEN` will **not** automatically trigger `on: pull_request` workflows (a developer must trigger CI manually or close/reopen the PR).

### Option C: Dedicated Machine User Account + PAT *(Exact Mirror of Upstream)*
1. Create a dedicated GitHub user account (e.g., `companyx-release-bot`).
2. Add it as a **Write collaborator / member** of your enterprise repository/organization.
3. Generate a Fine-Grained PAT for that account and store it as secret `GH_USER_TOKEN`.
* **Trade-off**: Creates a long-lived PAT requiring rotation, and consumes **1 billable user seat** if added as a member of a paid Organization.

---

## 4. Which Subscription Do I Need to Purchase?

| Deployment Option | GitHub Plan Required | Official GitHub Billing & Seat Policy | Annual Cost for Bot Identity |
| :--- | :--- | :--- | :--- |
| **Option A: GitHub App** *(Best Practice)* | **Any** (GitHub Free, Team, or Enterprise Cloud) | **GitHub App bot accounts do NOT consume a billable seat or license.** | **$0.00 / year** |
| **Option B: Built-in `GITHUB_TOKEN`** | **Any** (GitHub Free, Team, or Enterprise Cloud) | Native workflow token; no external account required. | **$0.00 / year** |
| **Option C: Dedicated Machine User + PAT** *(Public Repo on Free Tier)* | **GitHub Free** | Outside collaborators on public repos are free (lacks enterprise SAML/audit controls). | **$0.00 / year** |
| **Option C: Dedicated Machine User + PAT** *(GitHub Team)* | **GitHub Team** ($4/user/mo) | Adding a machine user as an org member consumes **1 paid seat**. | **$48 / year** for the bot seat *(or $240/yr for 5 seats total)* |
| **Option C: Dedicated Machine User + PAT** *(GitHub Enterprise Cloud)* | **GitHub Enterprise Cloud** ($21/user/mo) | Adding a machine user as an org/enterprise member consumes **1 paid seat**. | **$252 / year** for the bot seat |

> **Recommendation**: You do **not** need to purchase a separate subscription or extra user seat for `bot collaborator upstream`. Register a free internal **GitHub App (Option A)** on your existing GitHub organization—it provides full CI triggering parity with upstream, better credential security, and **$0.00/year** in additional licensing cost.
