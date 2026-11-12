#!/usr/bin/env python3
"""
check-runs.py - Comprehensive monitoring tool for GitHub Actions workflow runs.
Finds all passed, failed, running, queued, skipped pipelines, calculates durations,
and outputs a summary metric card.
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
    # Parse ISO8601 string (e.g. 2026-11-02T01:00:25Z)
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def format_duration(seconds):
    if seconds is None or seconds < 0:
        return "N/A"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    rem_seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {rem_seconds:02d}s"
    hours = minutes // 60
    rem_minutes = minutes % 60
    return f"{hours}h {rem_minutes:02d}m"


def main():
    parser = argparse.ArgumentParser(description="Monitor and analyze GitHub Actions runs.")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "sajuptpm/node1"),
                        help="GitHub repository in 'owner/repo' format (default: sajuptpm/node1)")
    parser.add_argument("--workflow", help="Filter runs by specific workflow file name (e.g. test-linux.yml)")
    parser.add_argument("--status", choices=["all", "completed", "in_progress", "queued"], default="all",
                        help="Filter by run status (default: all)")
    parser.add_argument("--conclusion", choices=["all", "success", "failure", "skipped", "cancelled"], default="all",
                        help="Filter by run conclusion (default: all)")
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of runs to fetch (default: 25)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

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

    if args.workflow:
        wf = args.workflow
        if not wf.endswith(".yml") and not wf.endswith(".yaml") and not wf.isdigit():
            wf = f"{wf}.yml"
        url = f"https://api.github.com/repos/{args.repo}/actions/workflows/{wf}/runs"
    else:
        url = f"https://api.github.com/repos/{args.repo}/actions/runs"

    params = {"per_page": min(args.limit, 100)}
    if args.status != "all":
        params["status"] = args.status

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"Failed to fetch runs (HTTP {resp.status_code}): {resp.text}")
        sys.exit(1)

    data = resp.json()
    runs = data.get("workflow_runs", [])

    # Filter conclusion if requested
    if args.conclusion != "all":
        runs = [r for r in runs if r.get("conclusion") == args.conclusion]

    if args.json:
        print(json.dumps(runs, indent=2))
        return

    # Metrics counters
    total_count = len(runs)
    passed_count = sum(1 for r in runs if r.get("conclusion") == "success")
    failed_count = sum(1 for r in runs if r.get("conclusion") == "failure")
    skipped_count = sum(1 for r in runs if r.get("conclusion") == "skipped")
    cancelled_count = sum(1 for r in runs if r.get("conclusion") == "cancelled")
    running_count = sum(1 for r in runs if r.get("status") == "in_progress")
    queued_count = sum(1 for r in runs if r.get("status") == "queued")

    durations = []
    rows = []
    now = datetime.datetime.now(datetime.timezone.utc)

    for r in runs:
        run_id = r["id"]
        name = r["name"]
        event = r["event"]
        status = r["status"]
        conclusion = r.get("conclusion") or "pending"

        created_at = parse_iso(r.get("run_started_at") or r.get("created_at"))
        updated_at = parse_iso(r.get("updated_at"))

        if status == "completed" and created_at and updated_at:
            dur = (updated_at - created_at).total_seconds()
            durations.append(dur)
            dur_str = format_duration(dur)
        elif status == "in_progress" and created_at:
            dur = (now - created_at).total_seconds()
            dur_str = f"running ({format_duration(dur)})"
        else:
            dur_str = "N/A"

        # Symbol mapping
        if conclusion == "success":
            badge = "[PASS]"
        elif conclusion == "failure":
            badge = "[FAIL]"
        elif conclusion == "skipped":
            badge = "[SKIP]"
        elif conclusion == "cancelled":
            badge = "[CANC]"
        elif status == "in_progress":
            badge = "[RUN ]"
        elif status == "queued":
            badge = "[WAIT]"
        else:
            badge = f"[{status[:4].upper()}]"

        date_str = created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if created_at else "N/A"
        rows.append({
            "badge": badge,
            "id": run_id,
            "name": name,
            "event": event,
            "duration": dur_str,
            "date": date_str,
            "url": r["html_url"],
        })

    print(f"\n==================== GitHub Actions Runs for {args.repo} ====================")
    print(f"{'Status':<9} {'Run ID':<13} {'Duration':<12} {'Event':<16} {'Workflow Name':<35} {'Started At'}")
    print("-" * 110)
    for row in rows:
        print(f"{row['badge']:<9} {row['id']:<13} {row['duration']:<12} {row['event']:<16} {row['name'][:34]:<35} {row['date']}")

    avg_duration = sum(durations) / len(durations) if durations else 0

    print("\n" + "=" * 55 + " Summary Metrics " + "=" * 55)
    print(f"Total Fetched:  {total_count:<6} | Passed:    {passed_count:<6} | Failed:    {failed_count:<6} | Running: {running_count:<6}")
    print(f"Skipped:        {skipped_count:<6} | Cancelled: {cancelled_count:<6} | Queued:    {queued_count:<6} | Avg Time: {format_duration(avg_duration)}")
    print("=" * 127 + "\n")


if __name__ == "__main__":
    main()
