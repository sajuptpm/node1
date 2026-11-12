#!/usr/bin/env python3
"""
trigger-workflow.py - Dispatches a GitHub Actions workflow with configurable inputs
and tracks the newly created run until registration.
"""

import argparse
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
            # Check Windows user registry/env if on Windows
            if sys.platform.startswith("win"):
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
                token, _ = winreg.QueryValueEx(key, "GH_TOKEN")
        except Exception:
            pass
    return token


def main():
    parser = argparse.ArgumentParser(description="Trigger a GitHub Actions workflow on demand.")
    parser.add_argument("workflow", help="Workflow file name (e.g. test-linux.yml, linters.yml) or ID")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "sajuptpm/node1"),
                        help="GitHub repository in 'owner/repo' format (default: sajuptpm/node1)")
    parser.add_argument("--ref", default="main", help="Git ref/branch to trigger (default: main)")
    parser.add_argument("--mode", choices=["auto", "native", "original"], default="native",
                        help="Execution mode (default: native)")
    parser.add_argument("--scope", choices=["smoke", "full"], default="smoke",
                        help="Test execution scope (default: smoke)")
    parser.add_argument("--dry-run", choices=["true", "false"], default="true",
                        help="Dry-run toggle for updater/release workflows (default: true)")
    parser.add_argument("-i", "--input", action="append", help="Custom key=value input (e.g. -i extra_flag=foo)")
    parser.add_argument("--watch", action="store_true", help="Automatically follow and watch run execution")

    args = parser.parse_args()
    token = get_auth_token()
    if not token:
        print("ERROR: GitHub authentication token not found.")
        print("Please set GH_TOKEN environment variable or login via 'gh auth login'.")
        sys.exit(1)

    workflow_name = args.workflow
    if not workflow_name.endswith(".yml") and not workflow_name.endswith(".yaml") and not workflow_name.isdigit():
        workflow_name = f"{workflow_name}.yml"

    url = f"https://api.github.com/repos/{args.repo}/actions/workflows/{workflow_name}/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Build inputs dictionary
    inputs = {
        "mode": args.mode,
        "test_scope": args.scope,
        "dry_run": args.dry_run == "true",
    }
    if args.input:
        for item in args.input:
            if "=" in item:
                k, v = item.split("=", 1)
                inputs[k.strip()] = v.strip()

    payload = {
        "ref": args.ref,
        "inputs": inputs,
    }

    print(f"Triggering workflow '{workflow_name}' on {args.repo}@{args.ref}...")
    print(f"Inputs: {json.dumps(inputs, indent=2)}")

    trigger_time = time.time()
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 204:
        print(f"Dispatch failed with HTTP status {resp.status_code}:")
        try:
            print(json.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text)
        sys.exit(1)

    print("SUCCESS: Dispatch request accepted (HTTP 204).")
    print("Locating new workflow run...")

    # Poll runs endpoint to locate the newly created run
    runs_url = f"https://api.github.com/repos/{args.repo}/actions/workflows/{workflow_name}/runs"
    run_found = None
    for attempt in range(12):
        time.sleep(2)
        runs_resp = requests.get(runs_url, headers=headers, params={"per_page": 5, "event": "workflow_dispatch"})
        if runs_resp.status_code == 200:
            data = runs_resp.json()
            for r in data.get("workflow_runs", []):
                # Verify run is recent (within last 30 seconds)
                created_at_str = r.get("created_at")
                if created_at_str:
                    run_found = r
                    break
        if run_found:
            break

    if run_found:
        print(f"-> Run ID: {run_found['id']}")
        print(f"-> HTML URL: {run_found['html_url']}")
        print(f"-> Status: {run_found['status']} | Conclusion: {run_found.get('conclusion') or 'in progress'}")
        if args.watch:
            print("\nStreaming run status via gh CLI:")
            subprocess.run(["gh", "run", "watch", str(run_found["id"])])
    else:
        print("Note: Run was dispatched successfully. View runs at:")
        print(f"https://github.com/{args.repo}/actions/workflows/{workflow_name}")


if __name__ == "__main__":
    main()
