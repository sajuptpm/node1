#!/usr/bin/env python3
"""
cancel-queued-runs.py - Cancels all active in-progress or queued workflow runs
to conserve GitHub Actions runner minutes and clean up the queue.
"""

import argparse
import os
import subprocess
import sys

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


def main():
    parser = argparse.ArgumentParser(description="Cancel active queued or in-progress workflow runs.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "sajuptpm/node1"),
                        help="GitHub repository in 'owner/repo' format (default: sajuptpm/node1)")
    parser.add_argument("--workflow", help="Filter by specific workflow name or file (e.g. test-linux.yml)")
    parser.add_argument("--dry-run", action="store_true", help="List active runs without sending cancellation requests")

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

    print(f"Checking for active runs in {args.repo}...")
    active_runs = []

    # Fetch queued runs
    for status in ["queued", "in_progress"]:
        url = f"https://api.github.com/repos/{args.repo}/actions/runs"
        resp = requests.get(url, headers=headers, params={"status": status, "per_page": 50})
        if resp.status_code == 200:
            data = resp.json().get("workflow_runs", [])
            for r in data:
                if args.workflow:
                    wf = args.workflow.lower()
                    r_name = r.get("name", "").lower()
                    r_path = r.get("path", "").lower()
                    if wf not in r_name and wf not in r_path:
                        continue
                active_runs.append(r)

    if not active_runs:
        print("No queued or in-progress workflow runs found. Queue is clean.")
        return

    print(f"Found {len(active_runs)} active run(s):")
    for r in active_runs:
        print(f" - [{r['status'].upper()}] ID: {r['id']} | {r['name']} (Event: {r['event']})")

    if args.dry_run:
        print("\nDry-run mode active. No cancellation requests sent.")
        return

    print("\nCancelling active runs...")
    cancelled_count = 0
    for r in active_runs:
        run_id = r["id"]
        cancel_url = f"https://api.github.com/repos/{args.repo}/actions/runs/{run_id}/cancel"
        c_resp = requests.post(cancel_url, headers=headers)
        if c_resp.status_code in [202, 204]:
            print(f"✓ Cancelled run {run_id} ({r['name']})")
            cancelled_count += 1
        else:
            print(f"Failed to cancel run {run_id}: HTTP {c_resp.status_code} ({c_resp.text})")

    print(f"\nDone: {cancelled_count} of {len(active_runs)} run(s) cancelled successfully.")


if __name__ == "__main__":
    main()
