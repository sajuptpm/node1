#!/usr/bin/env python3
"""
test-all-workflows.py - End-to-end suite runner for GitHub Actions.
Sequentially triggers and monitors workflows in native smoke mode, tracks execution
timelines, outcomes, and generates a structured markdown execution report.
"""

import argparse
import datetime
import glob
import json
import os
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    print("Error: 'requests' module is required. Install via: pip install requests")
    sys.exit(1)

# Ensure stdout supports UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_auth_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        try:
            res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                token = res.stdout.strip()
        except Exception:
            pass
    if not token:
        try:
            if sys.platform.startswith("win"):
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
                token, _ = winreg.QueryValueEx(key, "GH_TOKEN")
        except Exception:
            pass
    return token


def parse_iso(ts):
    if not ts:
        return None
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def format_duration(seconds):
    if seconds is None or seconds < 0:
        return "N/A"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m = seconds // 60
    s = seconds % 60
    return f"{m}m {s:02d}s"


def main():
    parser = argparse.ArgumentParser(description="Sequentially test all or selected GitHub Actions workflows.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "sajuptpm/node1"),
                        help="GitHub repository in 'owner/repo' format (default: sajuptpm/node1)")
    parser.add_argument("--ref", default="main", help="Git branch to trigger (default: main)")
    parser.add_argument("--mode", choices=["auto", "native", "original"], default="native",
                        help="Execution mode (default: native)")
    parser.add_argument("--scope", choices=["smoke", "full"], default="smoke",
                        help="Test execution scope (default: smoke)")
    parser.add_argument("--dry-run", action="store_true", help="Print workflow list without triggering dispatches")
    parser.add_argument("--interval", type=int, default=5, help="Sleep interval (seconds) between workflow tests")
    parser.add_argument("--timeout", type=int, default=180, help="Max seconds to wait per workflow execution (default: 180)")
    parser.add_argument("--workflows", help="Comma-separated list of workflow file names to test (omit to run all)")
    parser.add_argument("--report", default="workflow-fixes/test-suite-execution-report.md",
                        help="Output path for markdown report")

    args = parser.parse_args()
    token = get_auth_token()
    if not token:
        print("ERROR: GitHub authentication token not found. Set GH_TOKEN or login with 'gh auth login'.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    workflow_dir = os.path.join(root_dir, ".github", "workflows")

    if args.workflows:
        requested = [w.strip() for w in args.workflows.split(",") if w.strip()]
        workflow_files = []
        for w in requested:
            if not w.endswith(".yml") and not w.endswith(".yaml"):
                w = f"{w}.yml"
            full_path = os.path.join(workflow_dir, w)
            if os.path.exists(full_path):
                workflow_files.append(full_path)
            else:
                print(f"Warning: Workflow {w} not found in {workflow_dir}")
    else:
        workflow_files = sorted(glob.glob(os.path.join(workflow_dir, "*.yml")) + glob.glob(os.path.join(workflow_dir, "*.yaml")))

    print(f"\nDiscovered {len(workflow_files)} workflows to test on {args.repo}@{args.ref}:")
    for f in workflow_files:
        print(f" - {os.path.basename(f)}")

    if args.dry_run:
        print("\n[Dry Run] Execution preview complete. No dispatches were triggered.")
        return

    results = []
    print("\nStarting sequential execution...")
    print("=" * 105)

    for idx, fpath in enumerate(workflow_files, start=1):
        wf_name = os.path.basename(fpath)
        print(f"\n[{idx}/{len(workflow_files)}] Dispatching {wf_name}...")

        dispatch_url = f"https://api.github.com/repos/{args.repo}/actions/workflows/{wf_name}/dispatches"
        payload = {
            "ref": args.ref,
            "inputs": {
                "mode": args.mode,
                "test_scope": args.scope,
                "dry_run": True,
            }
        }

        t_start = time.time()
        disp_resp = requests.post(dispatch_url, headers=headers, json=payload)
        if disp_resp.status_code != 204:
            print(f"  ✖ Dispatch failed: HTTP {disp_resp.status_code}")
            results.append({
                "file": wf_name,
                "status": "DISPATCH_FAILED",
                "run_id": "N/A",
                "duration": "N/A",
                "url": "N/A"
            })
            continue

        # Poll for run registration
        runs_url = f"https://api.github.com/repos/{args.repo}/actions/workflows/{wf_name}/runs"
        run_obj = None
        for _ in range(15):
            time.sleep(2)
            r_resp = requests.get(runs_url, headers=headers, params={"per_page": 3, "event": "workflow_dispatch"})
            if r_resp.status_code == 200:
                runs_list = r_resp.json().get("workflow_runs", [])
                if runs_list:
                    run_obj = runs_list[0]
                    break

        if not run_obj:
            print("  ✖ Failed to locate triggered run.")
            results.append({
                "file": wf_name,
                "status": "TIMEOUT_LOCATING_RUN",
                "run_id": "N/A",
                "duration": "N/A",
                "url": "N/A"
            })
            continue

        run_id = run_obj["id"]
        run_url = run_obj["html_url"]
        print(f"  -> Run registered: {run_id} ({run_url})")

        # Monitor until completed or timeout
        status = run_obj.get("status")
        conclusion = run_obj.get("conclusion")
        poll_start = time.time()

        while status != "completed" and (time.time() - poll_start) < args.timeout:
            time.sleep(4)
            check_url = f"https://api.github.com/repos/{args.repo}/actions/runs/{run_id}"
            c_resp = requests.get(check_url, headers=headers)
            if c_resp.status_code == 200:
                c_data = c_resp.json()
                status = c_data.get("status")
                conclusion = c_data.get("conclusion")
                print(f"     Status: {status} | Conclusion: {conclusion or 'in progress'}", end="\r")

        dur = time.time() - t_start
        outcome = conclusion if status == "completed" else "TIMED_OUT"
        badge = "[PASS]" if outcome == "success" else f"[{outcome.upper()}]"
        print(f"\n  {badge} Run {run_id} finished: {outcome} ({format_duration(dur)})")

        results.append({
            "file": wf_name,
            "status": outcome,
            "run_id": str(run_id),
            "duration": format_duration(dur),
            "url": run_url
        })

        if idx < len(workflow_files):
            time.sleep(args.interval)

    # Print summary table
    print("\n" + "=" * 40 + " Suite Execution Summary " + "=" * 40)
    print(f"{'Workflow File':<35} {'Outcome':<12} {'Duration':<10} {'Run ID':<13} {'URL'}")
    print("-" * 110)
    for res in results:
        print(f"{res['file']:<35} {res['status']:<12} {res['duration']:<10} {res['run_id']:<13} {res['url']}")

    # Export markdown report
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write("# Full Suite Workflow Execution Report\n\n")
        f.write(f"- **Executed At**: `{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`\n")
        f.write(f"- **Repository**: `{args.repo}`\n")
        f.write(f"- **Branch/Ref**: `{args.ref}`\n")
        f.write(f"- **Mode**: `{args.mode}` | **Scope**: `{args.scope}`\n\n")
        f.write("| # | Workflow File | Outcome | Duration | Run ID | Run URL |\n")
        f.write("| :-: | :--- | :--- | :--- | :--- | :--- |\n")
        for i, res in enumerate(results, start=1):
            f.write(f"| {i} | `{res['file']}` | `{res['status']}` | `{res['duration']}` | [`{res['run_id']}`]({res['url']}) | [View Run]({res['url']}) |\n")

    print(f"\nMarkdown summary report exported to: {args.report}\n")


if __name__ == "__main__":
    main()
