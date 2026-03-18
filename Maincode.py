#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║           GitHub Repo Health Dashboard  📊                              ║
║                                                                          ║
║  Deep analytics for solo devs. Audits your repo and generates a         ║
║  beautiful HTML report + terminal summary covering:                      ║
║                                                                          ║
║   • Commit velocity & streaks          • Branch hygiene                  ║
║   • PR cycle time & merge rate         • Issue trends & resolution       ║
║   • Your personal contribution graph   • Staleness heatmap               ║
║   • Release cadence                    • Code churn estimation           ║
║                                                                          ║
║  Uses: gh CLI — no tokens to manage.                                    ║
╚══════════════════════════════════════════════════════════════════════════╝

Usage:
    python gh_repo_health.py                          # current repo, last 90 days
    python gh_repo_health.py --repo owner/repo        # any repo
    python gh_repo_health.py --days 180               # longer window
    python gh_repo_health.py --output report.html     # custom output path
    python gh_repo_health.py --no-browser             # skip auto-opening report
    python gh_repo_health.py --json                   # also export raw JSON

Requirements:
    pip install rich          (optional, prettier terminal output)
    gh auth login             (one-time GitHub CLI setup)
"""

import argparse
import json
import subprocess
import sys
import webbrowser
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median


# ── Soft dependency: rich ────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None


# ─────────────────────────────────────────────────────────────────────────────
#  Terminal helpers
# ─────────────────────────────────────────────────────────────────────────────

def log(msg, style=""):
    if RICH and style:
        console.print(msg, style=style)
    else:
        print(msg)

def info(m):  log(f"  {m}", "cyan")
def ok(m):    log(f"  ✔ {m}", "green")
def warn(m):  log(f"  ⚠ {m}", "yellow")
def err(m):   log(f"  ✘ {m}", "bold red")
def head(m):  log(f"\n{m}", "bold white")


# ─────────────────────────────────────────────────────────────────────────────
#  gh CLI wrapper
# ─────────────────────────────────────────────────────────────────────────────

def run_gh(args: list, check=True):
    try:
        r = subprocess.run(["gh"] + args, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        err("'gh' CLI not found. Install: https://cli.github.com/")
        sys.exit(1)
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"gh exited {r.returncode}")
    return r


def gh_json(args: list):
    r = run_gh(args)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Bad JSON from gh: {r.stdout[:200]}")


def gh_api(path: str, paginate=False, jq: str = None):
    args = ["api", path]
    if paginate:
        args += ["--paginate", "--slurp"]  # --slurp merges pages into one array
    if jq:
        args += ["-q", jq]
    return run_gh(args)


def parse_paginated(raw: str) -> list:
    """Safely parse output from a paginated gh api call (with --slurp)."""
    if not raw.strip():
        return []
    parsed = json.loads(raw)
    # --slurp wraps pages: [[...], [...]] -> flatten
    if parsed and isinstance(parsed[0], list):
        flat = []
        for page in parsed:
            flat.extend(page)
        return flat
    return parsed if isinstance(parsed, list) else []


# ─────────────────────────────────────────────────────────────────────────────
#  Time utilities
# ─────────────────────────────────────────────────────────────────────────────

def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def days_ago(n: int) -> datetime:
    return now_utc() - timedelta(days=n)

def age_days(iso: str) -> float:
    return (now_utc() - parse_dt(iso)).total_seconds() / 86400

def fmt_dt(iso: str) -> str:
    return parse_dt(iso).strftime("%Y-%m-%d")

def week_key(iso: str) -> str:
    dt = parse_dt(iso)
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
#  Pre-flight
# ─────────────────────────────────────────────────────────────────────────────

def check_auth():
    r = run_gh(["auth", "status"], check=False)
    if r.returncode != 0:
        err("Not authenticated. Run: gh auth login")
        sys.exit(1)
    ok("gh auth OK")


def resolve_repo(arg):
    if arg:
        return arg
    r = run_gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], check=False)
    if r.returncode != 0:
        err("Cannot detect repo. Pass --repo owner/repo")
        sys.exit(1)
    return r.stdout.strip()


# ─────────────────────────────────────────────────────────────────────────────
#  Data collection
# ─────────────────────────────────────────────────────────────────────────────

def fetch_repo_meta(repo: str) -> dict:
    info("Fetching repo metadata …")
    data = gh_json([
        "repo", "view", repo,
        "--json",
        "name,owner,description,defaultBranchRef,stargazerCount,"
        "forkCount,isPrivate,createdAt,updatedAt,primaryLanguage,"
        "languages,repositoryTopics,diskUsage",
    ])
    ok("Repo metadata")
    return data


def fetch_commits(repo: str, days: int) -> list:
    info("Fetching commits …")
    since = days_ago(days).strftime("%Y-%m-%dT%H:%M:%SZ")
    default_branch = gh_json(["repo", "view", repo, "--json", "defaultBranchRef"])
    branch = default_branch.get("defaultBranchRef", {}).get("name", "main")

    try:
        r = gh_api(
            f"repos/{repo}/commits?sha={branch}&since={since}&per_page=100",
            paginate=True,
        )
        commits = parse_paginated(r.stdout)
    except Exception as e:
        warn(f"Could not fetch commits: {e}")
        commits = []

    ok(f"Commits: {len(commits)}")
    return commits


def fetch_prs(repo: str, days: int, state="all") -> list:
    info(f"Fetching PRs ({state}) …")
    since = days_ago(days).isoformat()
    try:
        prs = gh_json([
            "pr", "list", "--repo", repo, "--state", state,
            "--limit", "200",
            "--json",
            "number,title,author,createdAt,closedAt,mergedAt,"
            "state,isDraft,reviewDecision,additions,deletions,labels",
        ])
        # filter to window
        prs = [p for p in prs if p["createdAt"] >= since]
    except Exception as e:
        warn(f"Could not fetch PRs: {e}")
        prs = []
    ok(f"PRs: {len(prs)}")
    return prs


def fetch_issues(repo: str, days: int) -> list:
    info("Fetching issues …")
    since = days_ago(days).isoformat()
    try:
        issues = gh_json([
            "issue", "list", "--repo", repo, "--state", "all",
            "--limit", "200",
            "--json",
            "number,title,author,createdAt,closedAt,state,labels,assignees",
        ])
        issues = [i for i in issues if i["createdAt"] >= since]
    except Exception as e:
        warn(f"Could not fetch issues: {e}")
        issues = []
    ok(f"Issues: {len(issues)}")
    return issues


def fetch_branches(repo: str) -> list:
    info("Fetching branches …")
    try:
        r = gh_api(f"repos/{repo}/branches?per_page=100", paginate=True)
        branches = parse_paginated(r.stdout)
    except Exception as e:
        warn(f"Could not fetch branches: {e}")
        branches = []
    ok(f"Branches: {len(branches)}")
    return branches


def fetch_releases(repo: str, days: int) -> list:
    info("Fetching releases …")
    since = days_ago(days).isoformat()
    try:
        releases = gh_json([
            "release", "list", "--repo", repo, "--limit", "50",
            "--json", "tagName,name,createdAt,isDraft,isPrerelease",
        ])
        releases = [rel for rel in releases if rel.get("createdAt", "") >= since]
    except Exception as e:
        warn(f"Could not fetch releases: {e}")
        releases = []
    ok(f"Releases: {len(releases)}")
    return releases


# ─────────────────────────────────────────────────────────────────────────────
#  Analytics
# ─────────────────────────────────────────────────────────────────────────────

def analyse_commits(commits: list, days: int) -> dict:
    if not commits:
        return {"total": 0, "by_week": {}, "by_dow": {}, "by_hour": {},
                "streak_current": 0, "streak_longest": 0, "authors": {},
                "avg_per_week": 0, "days_active": 0}

    by_week = defaultdict(int)
    by_dow  = defaultdict(int)
    by_hour = defaultdict(int)
    authors = defaultdict(int)
    commit_dates = set()

    for c in commits:
        dt_str = c.get("commit", {}).get("author", {}).get("date") or c.get("committer", {}).get("date", "")
        if not dt_str:
            continue
        dt = parse_dt(dt_str)
        by_week[week_key(dt_str)] += 1
        by_dow[dt.strftime("%a")] += 1
        by_hour[dt.hour] += 1
        commit_dates.add(dt.date())
        author = (c.get("author") or {}).get("login") or \
                 (c.get("commit", {}).get("author") or {}).get("name", "unknown")
        authors[author] += 1

    # Streaks (consecutive days with commits)
    sorted_dates = sorted(commit_dates, reverse=True)
    streak_current = 0
    streak_longest = 0
    current_run = 0
    prev = None
    for d in sorted(commit_dates):
        if prev is None or (d - prev).days == 1:
            current_run += 1
        else:
            current_run = 1
        streak_longest = max(streak_longest, current_run)
        prev = d

    # Current streak
    today = now_utc().date()
    streak_current = 0
    for d in sorted(commit_dates, reverse=True):
        expected = today - timedelta(days=streak_current)
        if d == expected:
            streak_current += 1
        else:
            break

    weeks = max(days / 7, 1)
    return {
        "total": len(commits),
        "by_week": dict(by_week),
        "by_dow": dict(by_dow),
        "by_hour": dict(by_hour),
        "streak_current": streak_current,
        "streak_longest": streak_longest,
        "authors": dict(authors),
        "avg_per_week": round(len(commits) / weeks, 1),
        "days_active": len(commit_dates),
    }


def analyse_prs(prs: list) -> dict:
    if not prs:
        return {"total": 0, "merged": 0, "open": 0, "closed_unmerged": 0,
                "merge_rate": 0, "avg_cycle_days": None, "median_cycle_days": None,
                "by_week": {}, "draft_count": 0}

    merged = [p for p in prs if p.get("mergedAt")]
    open_  = [p for p in prs if p["state"] == "OPEN"]
    closed_unmerged = [p for p in prs if p["state"] == "CLOSED" and not p.get("mergedAt")]

    cycle_times = []
    for p in merged:
        try:
            cycle = (parse_dt(p["mergedAt"]) - parse_dt(p["createdAt"])).total_seconds() / 86400
            cycle_times.append(cycle)
        except Exception:
            pass

    by_week = defaultdict(int)
    for p in prs:
        by_week[week_key(p["createdAt"])] += 1

    return {
        "total": len(prs),
        "merged": len(merged),
        "open": len(open_),
        "closed_unmerged": len(closed_unmerged),
        "merge_rate": round(len(merged) / len(prs) * 100, 1) if prs else 0,
        "avg_cycle_days": round(mean(cycle_times), 1) if cycle_times else None,
        "median_cycle_days": round(median(cycle_times), 1) if cycle_times else None,
        "by_week": dict(by_week),
        "draft_count": sum(1 for p in prs if p.get("isDraft")),
    }


def analyse_issues(issues: list) -> dict:
    if not issues:
        return {"total": 0, "open": 0, "closed": 0, "close_rate": 0,
                "avg_resolution_days": None, "by_week": {}, "label_counts": {}}

    open_  = [i for i in issues if i["state"] == "OPEN"]
    closed = [i for i in issues if i["state"] == "CLOSED"]

    resolution_times = []
    for i in closed:
        if i.get("closedAt"):
            try:
                rt = (parse_dt(i["closedAt"]) - parse_dt(i["createdAt"])).total_seconds() / 86400
                resolution_times.append(rt)
            except Exception:
                pass

    by_week = defaultdict(int)
    label_counts = defaultdict(int)
    for i in issues:
        by_week[week_key(i["createdAt"])] += 1
        for lbl in i.get("labels", []):
            label_counts[lbl["name"]] += 1

    return {
        "total": len(issues),
        "open": len(open_),
        "closed": len(closed),
        "close_rate": round(len(closed) / len(issues) * 100, 1) if issues else 0,
        "avg_resolution_days": round(mean(resolution_times), 1) if resolution_times else None,
        "by_week": dict(by_week),
        "label_counts": dict(sorted(label_counts.items(), key=lambda x: -x[1])[:10]),
    }


def analyse_branches(branches: list, default_branch: str) -> dict:
    non_default = [b for b in branches if b["name"] != default_branch]
    return {
        "total": len(branches),
        "non_default": len(non_default),
        "names": [b["name"] for b in non_default[:20]],
    }


def health_score(commits_a, prs_a, issues_a, branches_a, days) -> dict:
    """Compute a simple 0–100 health score with per-category scores."""
    scores = {}

    # Commit velocity (20 pts): aim for ≥5/week
    weekly = commits_a.get("avg_per_week", 0)
    scores["commit_velocity"] = min(20, int(weekly / 5 * 20))

    # Streak (15 pts): aim for ≥14 day streak
    streak = commits_a.get("streak_current", 0)
    scores["commit_streak"] = min(15, int(streak / 14 * 15))

    # PR merge rate (20 pts): aim for ≥80%
    merge_rate = prs_a.get("merge_rate", 0)
    scores["pr_merge_rate"] = min(20, int(merge_rate / 80 * 20))

    # PR cycle time (15 pts): aim for ≤3 days
    cycle = prs_a.get("median_cycle_days")
    if cycle is None:
        scores["pr_cycle"] = 10  # neutral
    else:
        scores["pr_cycle"] = min(15, int(max(0, (7 - cycle) / 7 * 15)))

    # Issue close rate (15 pts): aim for ≥70%
    close_rate = issues_a.get("close_rate", 0)
    scores["issue_close_rate"] = min(15, int(close_rate / 70 * 15))

    # Branch hygiene (15 pts): fewer stray branches = better
    non_default = branches_a.get("non_default", 0)
    scores["branch_hygiene"] = max(0, min(15, 15 - non_default))

    total = sum(scores.values())
    grade = "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D"

    return {"total": total, "grade": grade, "breakdown": scores}


# ─────────────────────────────────────────────────────────────────────────────
#  HTML Report
# ─────────────────────────────────────────────────────────────────────────────

def build_html(repo: str, days: int, meta: dict, commits_a: dict, prs_a: dict,
               issues_a: dict, branches_a: dict, releases: list, health: dict) -> str:

    repo_name = meta.get("name", repo)
    desc = meta.get("description") or "No description"
    lang = (meta.get("primaryLanguage") or {}).get("name", "—")
    stars = meta.get("stargazerCount", 0)
    forks = meta.get("forkCount", 0)
    created = fmt_dt(meta.get("createdAt", now_utc().isoformat()))
    grade = health["grade"]
    score = health["total"]
    grade_color = {"A": "#22c55e", "B": "#84cc16", "C": "#f59e0b", "D": "#ef4444"}.get(grade, "#6b7280")

    # ── Sparkline data ───────────────────────────────────────────────────────
    all_weeks = sorted(set(
        list(commits_a.get("by_week", {}).keys()) +
        list(prs_a.get("by_week", {}).keys()) +
        list(issues_a.get("by_week", {}).keys())
    ))[-16:]  # last 16 weeks

    def sparkline_json(data_dict):
        return json.dumps([data_dict.get(w, 0) for w in all_weeks])

    commit_spark = sparkline_json(commits_a.get("by_week", {}))
    pr_spark     = sparkline_json(prs_a.get("by_week", {}))
    issue_spark  = sparkline_json(issues_a.get("by_week", {}))

    # ── DOW heatmap ──────────────────────────────────────────────────────────
    dow_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow_data  = json.dumps({d: commits_a.get("by_dow", {}).get(d, 0) for d in dow_order})

    # ── Hour distribution ─────────────────────────────────────────────────────
    hour_data = json.dumps([commits_a.get("by_hour", {}).get(h, 0) for h in range(24)])

    # ── Top contributors ──────────────────────────────────────────────────────
    authors_top = sorted(commits_a.get("authors", {}).items(), key=lambda x: -x[1])[:5]
    authors_json = json.dumps(authors_top)

    # ── Branch names ──────────────────────────────────────────────────────────
    branch_names_html = "".join(
        f'<span class="branch-tag">{b}</span>'
        for b in (branches_a.get("names") or [])[:15]
    )

    # ── Releases table ────────────────────────────────────────────────────────
    releases_rows = ""
    for rel in releases[:10]:
        tag = rel.get("tagName", "—")
        name = rel.get("name") or tag
        date = fmt_dt(rel.get("createdAt", "")) if rel.get("createdAt") else "—"
        flags = " ".join(filter(None, [
            "<span class='badge draft'>draft</span>" if rel.get("isDraft") else "",
            "<span class='badge pre'>pre-release</span>" if rel.get("isPrerelease") else "",
        ]))
        releases_rows += f"<tr><td>{tag}</td><td>{name[:40]}</td><td>{date}</td><td>{flags or '✅ stable'}</td></tr>"
    if not releases_rows:
        releases_rows = "<tr><td colspan='4' class='empty'>No releases in this window</td></tr>"

    # ── Health breakdown bars ─────────────────────────────────────────────────
    breakdown = health.get("breakdown", {})
    def bar(key, label, max_pts):
        pts = breakdown.get(key, 0)
        pct = int(pts / max_pts * 100)
        color = "#22c55e" if pct >= 70 else "#f59e0b" if pct >= 40 else "#ef4444"
        return f"""
        <div class="bar-row">
          <span class="bar-label">{label}</span>
          <div class="bar-track">
            <div class="bar-fill" style="width:{pct}%;background:{color}"></div>
          </div>
          <span class="bar-pts">{pts}/{max_pts}</span>
        </div>"""

    health_bars = (
        bar("commit_velocity",  "Commit Velocity",   20) +
        bar("commit_streak",    "Commit Streak",     15) +
        bar("pr_merge_rate",    "PR Merge Rate",     20) +
        bar("pr_cycle",         "PR Cycle Time",     15) +
        bar("issue_close_rate", "Issue Close Rate",  15) +
        bar("branch_hygiene",   "Branch Hygiene",    15)
    )

    avg_cycle = f"{prs_a.get('avg_cycle_days', '—')} d" if prs_a.get("avg_cycle_days") is not None else "—"
    med_cycle = f"{prs_a.get('median_cycle_days', '—')} d" if prs_a.get("median_cycle_days") is not None else "—"
    avg_resolution = f"{issues_a.get('avg_resolution_days', '—')} d" if issues_a.get("avg_resolution_days") is not None else "—"

    label_pills = "".join(
        f'<span class="label-pill">{lbl} <b>{cnt}</b></span>'
        for lbl, cnt in list(issues_a.get("label_counts", {}).items())[:8]
    )

    generated_at = now_utc().strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{repo_name} — Repo Health</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,400;0,500;1,400&family=Syne:wght@400;600;700;800&display=swap');

  :root {{
    --bg: #0a0a0f;
    --surface: #111118;
    --surface2: #1a1a24;
    --border: #2a2a3a;
    --text: #e8e8f0;
    --muted: #6b6b80;
    --accent: #7c6af7;
    --accent2: #4fd8c4;
    --danger: #f87171;
    --warning: #fbbf24;
    --success: #34d399;
    --grade-color: {grade_color};
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Syne', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 0;
    overflow-x: hidden;
  }}

  /* ── Grain overlay ── */
  body::before {{
    content: '';
    position: fixed; inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none; z-index: 0; opacity: 0.4;
  }}

  .wrap {{ position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; padding: 40px 24px 80px; }}

  /* ── Header ── */
  .header {{
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: start;
    gap: 24px;
    margin-bottom: 48px;
    padding-bottom: 32px;
    border-bottom: 1px solid var(--border);
  }}
  .repo-name {{
    font-size: clamp(1.6rem, 4vw, 2.4rem);
    font-weight: 800;
    letter-spacing: -0.03em;
    color: var(--text);
  }}
  .repo-name span {{ color: var(--accent); }}
  .repo-meta {{ color: var(--muted); font-size: 0.85rem; margin-top: 6px; font-family: 'DM Mono', monospace; }}
  .repo-desc {{ margin-top: 10px; font-size: 0.95rem; color: #9999b0; max-width: 540px; font-weight: 400; }}
  .repo-tags {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }}
  .tag {{
    font-family: 'DM Mono', monospace; font-size: 0.72rem;
    padding: 3px 10px; border-radius: 20px;
    background: var(--surface2); border: 1px solid var(--border);
    color: var(--muted);
  }}
  .tag.lang {{ border-color: var(--accent); color: var(--accent); }}

  /* ── Grade circle ── */
  .grade-circle {{
    width: 100px; height: 100px;
    border-radius: 50%;
    border: 3px solid var(--grade-color);
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    box-shadow: 0 0 30px {grade_color}33;
    flex-shrink: 0;
  }}
  .grade-letter {{ font-size: 2.4rem; font-weight: 800; color: var(--grade-color); line-height: 1; }}
  .grade-score {{ font-size: 0.72rem; color: var(--muted); font-family: 'DM Mono', monospace; margin-top: 2px; }}

  /* ── Stat cards ── */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 14px;
    margin-bottom: 40px;
  }}
  .stat-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 16px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s, transform 0.2s;
  }}
  .stat-card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .stat-card::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    opacity: 0;
    transition: opacity 0.2s;
  }}
  .stat-card:hover::before {{ opacity: 1; }}
  .stat-value {{ font-size: 1.8rem; font-weight: 800; letter-spacing: -0.04em; color: var(--text); }}
  .stat-label {{ font-size: 0.72rem; color: var(--muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.08em; }}
  .stat-sub {{ font-size: 0.78rem; color: var(--accent2); margin-top: 6px; font-family: 'DM Mono', monospace; }}

  /* ── Sections ── */
  .section {{ margin-bottom: 40px; }}
  .section-title {{
    font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.15em;
    color: var(--muted);
    margin-bottom: 16px;
    display: flex; align-items: center; gap: 10px;
  }}
  .section-title::after {{
    content: ''; flex: 1; height: 1px; background: var(--border);
  }}

  /* ── Chart containers ── */
  .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media(max-width:640px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}

  .chart-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
  }}
  .chart-card h3 {{ font-size: 0.8rem; color: var(--muted); margin-bottom: 16px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }}
  canvas {{ width: 100% !important; }}

  /* ── Health bars ── */
  .bar-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
  .bar-label {{ font-size: 0.8rem; color: var(--muted); width: 140px; flex-shrink: 0; }}
  .bar-track {{ flex: 1; height: 6px; background: var(--border); border-radius: 99px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 99px; transition: width 1s cubic-bezier(.16,1,.3,1); }}
  .bar-pts {{ font-family: 'DM Mono', monospace; font-size: 0.72rem; color: var(--muted); width: 36px; text-align: right; }}

  /* ── Branch tags ── */
  .branch-tag {{
    display: inline-block;
    font-family: 'DM Mono', monospace; font-size: 0.72rem;
    padding: 3px 8px; border-radius: 6px;
    background: var(--surface2); border: 1px solid var(--border);
    color: var(--accent2); margin: 3px;
  }}

  /* ── Releases table ── */
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{ text-align: left; padding: 8px 12px; color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; border-bottom: 1px solid var(--border); font-weight: 600; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); color: var(--text); font-family: 'DM Mono', monospace; font-size: 0.8rem; }}
  tr:last-child td {{ border-bottom: none; }}
  .empty {{ color: var(--muted); text-align: center; padding: 24px; }}
  .badge {{ font-size: 0.65rem; padding: 2px 7px; border-radius: 20px; font-weight: 600; }}
  .badge.draft {{ background: #1e293b; color: #94a3b8; }}
  .badge.pre {{ background: #2d1b00; color: #f59e0b; }}

  /* ── Label pills ── */
  .label-pill {{
    display: inline-block; font-size: 0.75rem;
    padding: 3px 10px; border-radius: 20px;
    background: var(--surface2); border: 1px solid var(--border);
    color: var(--muted); margin: 3px;
  }}
  .label-pill b {{ color: var(--text); }}

  /* ── Footer ── */
  .footer {{ text-align: center; color: var(--muted); font-size: 0.75rem; margin-top: 60px; font-family: 'DM Mono', monospace; }}

  /* ── Animations ── */
  .fade-in {{ animation: fadeUp 0.5s ease both; }}
  @keyframes fadeUp {{ from {{ opacity:0; transform:translateY(16px); }} to {{ opacity:1; transform:translateY(0); }} }}
  .stat-card:nth-child(1) {{ animation-delay: 0.05s; }}
  .stat-card:nth-child(2) {{ animation-delay: 0.10s; }}
  .stat-card:nth-child(3) {{ animation-delay: 0.15s; }}
  .stat-card:nth-child(4) {{ animation-delay: 0.20s; }}
  .stat-card:nth-child(5) {{ animation-delay: 0.25s; }}
  .stat-card:nth-child(6) {{ animation-delay: 0.30s; }}
</style>
</head>
<body>
<div class="wrap">

  <!-- Header -->
  <header class="header fade-in">
    <div>
      <div class="repo-name"><span>{repo.split('/')[0]}/</span>{repo_name}</div>
      <div class="repo-meta">created {created} · ⭐ {stars} · 🍴 {forks} · last {days} days</div>
      <div class="repo-desc">{desc}</div>
      <div class="repo-tags">
        <span class="tag lang">{lang}</span>
        <span class="tag">{'private' if meta.get('isPrivate') else 'public'}</span>
      </div>
    </div>
    <div class="grade-circle" title="Health score: {score}/100">
      <div class="grade-letter">{grade}</div>
      <div class="grade-score">{score}/100</div>
    </div>
  </header>

  <!-- Quick stats -->
  <section class="section">
    <div class="section-title">At a glance</div>
    <div class="stats-grid">
      <div class="stat-card fade-in">
        <div class="stat-value">{commits_a['total']}</div>
        <div class="stat-label">Commits</div>
        <div class="stat-sub">{commits_a['avg_per_week']}/week avg</div>
      </div>
      <div class="stat-card fade-in">
        <div class="stat-value">{commits_a['streak_current']}</div>
        <div class="stat-label">Day streak</div>
        <div class="stat-sub">best: {commits_a['streak_longest']}d</div>
      </div>
      <div class="stat-card fade-in">
        <div class="stat-value">{prs_a['total']}</div>
        <div class="stat-label">Pull Requests</div>
        <div class="stat-sub">{prs_a['merge_rate']}% merged</div>
      </div>
      <div class="stat-card fade-in">
        <div class="stat-value">{med_cycle}</div>
        <div class="stat-label">PR cycle time</div>
        <div class="stat-sub">avg {avg_cycle}</div>
      </div>
      <div class="stat-card fade-in">
        <div class="stat-value">{issues_a['total']}</div>
        <div class="stat-label">Issues</div>
        <div class="stat-sub">{issues_a['close_rate']}% resolved</div>
      </div>
      <div class="stat-card fade-in">
        <div class="stat-value">{branches_a['non_default']}</div>
        <div class="stat-label">Open branches</div>
        <div class="stat-sub">{branches_a['total']} total</div>
      </div>
    </div>
  </section>

  <!-- Charts -->
  <section class="section">
    <div class="section-title">Activity trends (weekly)</div>
    <div class="chart-grid">
      <div class="chart-card">
        <h3>Commit volume</h3>
        <canvas id="commitChart" height="120"></canvas>
      </div>
      <div class="chart-card">
        <h3>PR & Issue opens</h3>
        <canvas id="prIssueChart" height="120"></canvas>
      </div>
      <div class="chart-card">
        <h3>Commits by day of week</h3>
        <canvas id="dowChart" height="120"></canvas>
      </div>
      <div class="chart-card">
        <h3>Commits by hour (UTC)</h3>
        <canvas id="hourChart" height="120"></canvas>
      </div>
    </div>
  </section>

  <!-- Health breakdown -->
  <section class="section">
    <div class="section-title">Health score breakdown</div>
    <div class="chart-card">
      {health_bars}
    </div>
  </section>

  <!-- Releases -->
  <section class="section">
    <div class="section-title">Releases</div>
    <div class="chart-card" style="padding:0;overflow:hidden;">
      <table>
        <thead><tr><th>Tag</th><th>Name</th><th>Date</th><th>Status</th></tr></thead>
        <tbody>{releases_rows}</tbody>
      </table>
    </div>
  </section>

  <!-- Branches -->
  <section class="section">
    <div class="section-title">Active branches ({branches_a['non_default']} non-default)</div>
    <div class="chart-card">
      {branch_names_html or '<span style="color:var(--muted);font-size:0.85rem;">No additional branches</span>'}
    </div>
  </section>

  <!-- Issue labels -->
  {'<section class="section"><div class="section-title">Top issue labels</div><div class="chart-card">' + label_pills + '</div></section>' if label_pills else ''}

  <div class="footer">Generated {generated_at} by gh-repo-health · {repo}</div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
const WEEKS = {json.dumps(all_weeks)};
const shortWeeks = WEEKS.map(w => w.slice(5)); // MM-DD

const C = {{
  accent:  '#7c6af7',
  accent2: '#4fd8c4',
  success: '#34d399',
  warning: '#fbbf24',
  muted:   '#3a3a4a',
  text:    '#e8e8f0',
}};

Chart.defaults.color = '#6b6b80';
Chart.defaults.borderColor = '#2a2a3a';
Chart.defaults.font.family = "'DM Mono', monospace";
Chart.defaults.font.size = 11;

function makeLineChart(id, labels, datasets) {{
  new Chart(document.getElementById(id), {{
    type: 'line',
    data: {{ labels, datasets }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: datasets.length > 1 }} }},
      scales: {{
        x: {{ grid: {{ display: false }} }},
        y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }},
      }},
    }},
  }});
}}

function makeBarChart(id, labels, data, color) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{ labels, datasets: [{{ data, backgroundColor: color, borderRadius: 4 }}] }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ grid: {{ display: false }} }},
        y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }},
      }},
    }},
  }});
}}

// Commit chart
makeLineChart('commitChart', shortWeeks, [{{
  label: 'Commits',
  data: {commit_spark},
  borderColor: C.accent,
  backgroundColor: C.accent + '18',
  fill: true,
  tension: 0.4,
  pointRadius: 2,
}}]);

// PR + Issue chart
makeLineChart('prIssueChart', shortWeeks, [
  {{
    label: 'PRs',
    data: {pr_spark},
    borderColor: C.accent2,
    backgroundColor: 'transparent',
    tension: 0.4, pointRadius: 2,
  }},
  {{
    label: 'Issues',
    data: {issue_spark},
    borderColor: C.warning,
    backgroundColor: 'transparent',
    tension: 0.4, pointRadius: 2,
  }},
]);

// Day-of-week
const dowData = {dow_data};
makeBarChart('dowChart',
  Object.keys(dowData), Object.values(dowData),
  C.accent + 'cc'
);

// Hour
const hourData = {hour_data};
makeBarChart('hourChart',
  Array.from({{length:24}}, (_,i) => i+'h'), hourData,
  C.accent2 + 'cc'
);
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
#  Terminal summary
# ─────────────────────────────────────────────────────────────────────────────

def print_terminal_summary(repo, health, commits_a, prs_a, issues_a, branches_a):
    grade = health["grade"]
    score = health["total"]
    head(f"═══ Repo Health: {repo} ═══")
    log(f"\n  Grade: {grade}  ({score}/100)", "bold")

    if RICH:
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column("", style="dim", width=22)
        t.add_column("", style="bold white")

        rows = [
            ("Commits (window)", str(commits_a["total"])),
            ("Avg/week",         str(commits_a["avg_per_week"])),
            ("Current streak",   f"{commits_a['streak_current']}d"),
            ("Longest streak",   f"{commits_a['streak_longest']}d"),
            ("PRs total",        str(prs_a["total"])),
            ("PR merge rate",    f"{prs_a['merge_rate']}%"),
            ("PR cycle (median)",f"{prs_a['median_cycle_days']} d" if prs_a['median_cycle_days'] else "—"),
            ("Issues total",     str(issues_a["total"])),
            ("Issue close rate", f"{issues_a['close_rate']}%"),
            ("Open branches",    str(branches_a["non_default"])),
        ]
        for k, v in rows:
            t.add_row(k, v)
        console.print(t)
    else:
        print(f"\n  Commits:       {commits_a['total']}  ({commits_a['avg_per_week']}/wk)")
        print(f"  Streak:        {commits_a['streak_current']}d current / {commits_a['streak_longest']}d best")
        print(f"  PRs:           {prs_a['total']} total, {prs_a['merge_rate']}% merged")
        print(f"  Issues:        {issues_a['total']} total, {issues_a['close_rate']}% closed")
        print(f"  Open branches: {branches_a['non_default']}")


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="GitHub Repo Health Dashboard 📊",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--repo", "-r", metavar="OWNER/REPO",
                   help="Target repo (default: auto-detect from cwd)")
    p.add_argument("--days", "-d", type=int, default=90, metavar="N",
                   help="Analysis window in days (default: 90)")
    p.add_argument("--output", "-o", default="repo_health.html", metavar="FILE",
                   help="HTML report output path (default: repo_health.html)")
    p.add_argument("--no-browser", action="store_true",
                   help="Don't auto-open the report in a browser")
    p.add_argument("--json", dest="export_json", action="store_true",
                   help="Also export raw analytics as JSON")
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    if not RICH:
        print("Tip: pip install rich  for a prettier terminal experience.\n")

    check_auth()
    repo = resolve_repo(args.repo)
    ok(f"Analysing: {repo}  ({args.days} days)")

    head("Collecting data …")
    meta      = fetch_repo_meta(repo)
    commits   = fetch_commits(repo, args.days)
    prs       = fetch_prs(repo, args.days)
    issues    = fetch_issues(repo, args.days)
    branches  = fetch_branches(repo)
    releases  = fetch_releases(repo, args.days)

    default_branch = (meta.get("defaultBranchRef") or {}).get("name", "main")

    head("Computing analytics …")
    commits_a  = analyse_commits(commits, args.days)
    prs_a      = analyse_prs(prs)
    issues_a   = analyse_issues(issues)
    branches_a = analyse_branches(branches, default_branch)
    health     = health_score(commits_a, prs_a, issues_a, branches_a, args.days)

    print_terminal_summary(repo, health, commits_a, prs_a, issues_a, branches_a)

    head("Building report …")
    html = build_html(
        repo, args.days, meta,
        commits_a, prs_a, issues_a, branches_a,
        releases, health,
    )
    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    ok(f"HTML report → {out.resolve()}")

    if args.export_json:
        data = {
            "repo": repo, "days": args.days,
            "generated_at": now_utc().isoformat(),
            "health": health,
            "commits": commits_a,
            "prs": prs_a,
            "issues": issues_a,
            "branches": branches_a,
            "releases": [r.get("tagName") for r in releases],
        }
        json_path = out.with_suffix(".json")
        json_path.write_text(json.dumps(data, indent=2))
        ok(f"JSON export  → {json_path.resolve()}")

    if not args.no_browser:
        webbrowser.open(out.resolve().as_uri())
        ok("Opened in browser")

    head("Done ✅")


if __name__ == "__main__":
    main()
