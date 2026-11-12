#!/usr/bin/env python3
"""
check-run-jobs.py - Deep inspect a specific GitHub Actions workflow run.
Displays job status, duration, runner pool label, and step-by-step execution timeline.
"""

import argparse
import datetime
import json
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


def parse_iso(ts):
    if not ts:
        return None
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def format_duration(seconds):
    if seconds is None or seconds < 0:
        return "0s"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m = seconds // 60
    s = seconds % 60
    return f"{m}m {s:02d}s"


def main():
    parser = argparse.ArgumentParser(description="Inspect job and step details for a GitHub Actions workflow run.")
    parser.add_argument("run_id", nargs="?", help="GitHub Actions Run ID (defaults to latest run if omitted)")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "sajuptpm/node1"),
                        help="GitHub repository in 'owner/repo' format (default: sajuptpm/node1)")

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

    run_id = args.run_id
    if not run_id:
        # Fetch latest run
        runs_url = f"https://api.github.com/repos/{args.repo}/actions/runs"
        r_resp = requests.get(runs_url, headers=headers, params={"per_page": 1})
        if r_resp.status_code == 200 and r_resp.json().get("workflow_runs"):
            run_id = str(r_resp.json()["workflow_runs"][0]["id"])
            print(f"No Run ID provided; selecting latest run: {run_id}")
        else:
            print("Failed to fetch latest run ID.")
            sys.exit(1)

    # Fetch run metadata
    run_url = f"https://api.github.com/repos/{args.repo}/actions/runs/{run_id}"
    run_resp = requests.get(run_url, headers=headers)
    if run_resp.status_code != 200:
        print(f"Failed to fetch run {run_id}: HTTP {run_resp.status_code}")
        sys.exit(1)
    run_data = run_resp.json()

    print("\n" + "=" * 40 + f" Run Details: {run_id} " + "=" * 40)
    print(f"Workflow:    {run_data.get('name')}")
    print(f"Event:       {run_data.get('event')}")
    print(f"Branch/Ref:  {run_data.get('head_branch')}")
    print(f"Status:      {run_data.get('status')} | Conclusion: {run_data.get('conclusion') or 'in progress'}")
    print(f"URL:         {run_data.get('html_url')}")

    # Fetch jobs
    jobs_url = f"https://api.github.com/repos/{args.repo}/actions/runs/{run_id}/jobs"
    jobs_resp = requests.get(jobs_url, headers=headers)
    if jobs_resp.status_code != 200:
        print(f"Failed to fetch jobs for run {run_id}: HTTP {jobs_resp.status_code}")
        sys.exit(1)

    jobs = jobs_resp.json().get("jobs", [])
    print(f"\nTotal Jobs: {len(jobs)}")
    print("-" * 105)

    for job in jobs:
        j_name = job.get("name")
        j_id = job.get("id")
        j_status = job.get("status")
        j_concl = job.get("conclusion") or "running"
        j_runner = job.get("runner_name") or "GitHub Hosted"

        started_at = parse_iso(job.get("started_at"))
        completed_at = parse_iso(job.get("completed_at"))
        dur = (completed_at - started_at).total_seconds() if (started_at and completed_at) else None

        print(f"\n[JOB] {j_name} (ID: {j_id})")
        print(f"      Runner: {j_runner} | Status: {j_status} | Conclusion: {j_concl} | Duration: {format_duration(dur)}")
        print(f"      {'Step #':<8} {'Status':<10} {'Duration':<10} {'Step Name'}")
        print(f"      {'-'*95}")

        steps = job.get("steps", [])
        for step in steps:
            s_num = step.get("number")
            s_name = step.get("name")
            s_status = step.get("status")
            s_concl = step.get("conclusion") or s_status

            s_start = parse_iso(step.get("started_at"))
            s_end = parse_iso(step.get("completed_at"))
            s_dur = (s_end - s_start).total_seconds() if (s_start and s_end) else None

            print(f"      {s_num:<8} {s_concl:<10} {format_duration(s_dur):<10} {s_name}")

    print("\n" + "=" * 105 + "\n")


if __name__ == "__main__":
    main()
