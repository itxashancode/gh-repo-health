<div align="center">

```
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   ██████╗ ██╗  ██╗    ██████╗ ███████╗██████╗  ██████╗             ║
║  ██╔════╝ ██║  ██║    ██╔══██╗██╔════╝██╔══██╗██╔═══██╗            ║
║  ██║  ███╗███████║    ██████╔╝█████╗  ██████╔╝██║   ██║            ║
║  ██║   ██║██╔══██║    ██╔══██╗██╔══╝  ██╔═══╝ ██║   ██║            ║
║  ╚██████╔╝██║  ██║    ██║  ██║███████╗██║      ╚██████╔╝            ║
║   ╚═════╝ ╚═╝  ╚═╝    ╚═╝  ╚═╝╚══════╝╚═╝       ╚═════╝            ║
║                                                                      ║
║         H E A L T H   D A S H B O A R D   📊                       ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Deep repo analytics for solo devs — zero config, zero tokens.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-7c6af7?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![GitHub CLI](https://img.shields.io/badge/requires-gh%20CLI-4fd8c4?style=flat-square&logo=github&logoColor=white)](https://cli.github.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-34d399?style=flat-square)](LICENSE)
[![No tokens needed](https://img.shields.io/badge/auth-gh%20CLI%20only-fbbf24?style=flat-square&logo=githubactions&logoColor=white)](https://cli.github.com/)

</div>

---

## ✦ What it does

`gh-repo-health` audits any GitHub repository and renders a **beautiful dark-mode HTML dashboard** plus a rich terminal summary — in seconds, with no API tokens to manage.

<div align="center">

```
┌─────────────────────────────────────────────────────────┐
│  owner/repo                                    ┌───────┐ │
│  created 2023-01-15 · ⭐ 412 · 🍴 38           │   A   │ │
│  A blazing-fast tool for repo analytics.       │ 91/100│ │
│  ◆ Python  ◆ public                            └───────┘ │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│ 247      │ 12       │ 34       │ 1.2d     │ 89%         │
│ Commits  │Day streak│  PRs     │Cycle time│Issue close  │
└──────────┴──────────┴──────────┴──────────┴─────────────┘
```

</div>

### Metrics covered

| Category | What's measured |
|---|---|
| **Commit velocity** | Total commits, weekly average, active days |
| **Streaks** | Current & longest consecutive commit day streaks |
| **PR health** | Total PRs, merge rate, avg & median cycle time |
| **Issue trends** | Open/closed ratio, resolution time, top labels |
| **Branch hygiene** | Non-default branch count, stale branch detection |
| **Release cadence** | Releases in window, draft/pre-release flags |
| **Contribution patterns** | Commits by day-of-week and hour-of-day heatmaps |
| **Health score** | A–D letter grade with per-category breakdown (0–100) |

---

## ⚡ Quick start

```bash
# 1. Install the GitHub CLI (if you haven't)
#    https://cli.github.com/

# 2. Authenticate once
gh auth login

# 3. Clone & run inside any repo
git clone https://github.com/your-username/gh-repo-health
cd gh-repo-health

pip install rich          # optional — prettier terminal output

python gh_repo_health.py  # auto-detects current repo, opens HTML report
```

**That's it.** The script auto-detects your current repo, fetches all data via `gh`, and opens the HTML report in your browser. No `.env` files, no secrets, no setup beyond the one-time `gh auth login`.

---

## 🛠  Usage

```
python gh_repo_health.py [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `--repo`, `-r` | auto-detect | Target repo as `owner/repo` |
| `--days`, `-d` | `90` | Analysis window in days |
| `--output`, `-o` | `repo_health.html` | HTML report output path |
| `--no-browser` | `false` | Skip auto-opening the report |
| `--json` | `false` | Also export raw analytics as `.json` |

### Examples

```bash
# Analyse a specific repo
python gh_repo_health.py --repo torvalds/linux

# Longer 6-month window
python gh_repo_health.py --days 180

# Export JSON alongside HTML, don't open browser
python gh_repo_health.py --json --no-browser

# Save report to a custom path
python gh_repo_health.py --output ~/reports/my-project.html
```

---

## 📊 Health score

The dashboard computes a **0–100 health score** (letter grade A–D) from six weighted signals:

```
Commit Velocity    ████████████████████  20 pts  (target: ≥ 5 commits/week)
PR Merge Rate      ████████████████████  20 pts  (target: ≥ 80% merged)
Commit Streak      ███████████████       15 pts  (target: ≥ 14-day streak)
PR Cycle Time      ███████████████       15 pts  (target: ≤ 3 days median)
Issue Close Rate   ███████████████       15 pts  (target: ≥ 70% closed)
Branch Hygiene     ███████████████       15 pts  (fewer stray branches = better)
```

Grades: **A** ≥ 85 · **B** ≥ 70 · **C** ≥ 55 · **D** < 55

---

## 🖼  Output examples

### Terminal output (with `rich`)

```
  ✔ gh auth OK
  ✔ Analysing: acme/my-project  (90 days)

  Collecting data …
  ✔ Repo metadata
  ✔ Commits: 247
  ✔ PRs: 34
  ✔ Issues: 18
  ✔ Branches: 6
  ✔ Releases: 3

  Computing analytics …

═══ Repo Health: acme/my-project ═══

  Grade: A  (91/100)

  Commits (window)     247
  Avg/week             19.0
  Current streak       12d
  Longest streak       21d
  PRs total            34
  PR merge rate        91.2%
  PR cycle (median)    1.2 d
  Issues total         18
  Issue close rate     89%
  Open branches        3

  ✔ HTML report → /home/user/projects/my-project/repo_health.html
  ✔ Opened in browser
```

### JSON output (`--json` flag)

```json
{
  "repo": "acme/my-project",
  "days": 90,
  "generated_at": "2024-11-15T10:32:45.123456+00:00",
  "health": {
    "total": 91,
    "grade": "A",
    "breakdown": {
      "commit_velocity": 20,
      "commit_streak": 13,
      "pr_merge_rate": 20,
      "pr_cycle": 15,
      "issue_close_rate": 15,
      "branch_hygiene": 12
    }
  },
  "commits": {
    "total": 247,
    "avg_per_week": 19.0,
    "streak_current": 12,
    "streak_longest": 21,
    "days_active": 58,
    "by_week": {
      "2024-10-28": 14,
      "2024-11-04": 22,
      "2024-11-11": 18
    },
    "by_dow": { "Mon": 41, "Tue": 55, "Wed": 48, "Thu": 49, "Fri": 38, "Sat": 9, "Sun": 7 },
    "by_hour": [0,0,1,0,0,0,2,5,12,18,22,19,16,14,17,20,18,14,10,7,4,2,1,0],
    "authors": { "alice": 189, "dependabot": 58 }
  },
  "prs": {
    "total": 34,
    "merged": 31,
    "open": 2,
    "closed_unmerged": 1,
    "merge_rate": 91.2,
    "avg_cycle_days": 1.8,
    "median_cycle_days": 1.2,
    "draft_count": 2,
    "by_week": { "2024-10-28": 4, "2024-11-04": 6, "2024-11-11": 5 }
  },
  "issues": {
    "total": 18,
    "open": 2,
    "closed": 16,
    "close_rate": 88.9,
    "avg_resolution_days": 3.4,
    "label_counts": { "bug": 7, "enhancement": 6, "documentation": 3, "good first issue": 2 }
  },
  "branches": ["feature/dark-mode", "fix/auth-race", "chore/deps"],
  "releases": ["v2.1.0", "v2.0.3", "v2.0.2"]
}
```

The JSON export is ideal for piping into `jq`, feeding into CI dashboards, or building your own tooling on top.

---

## 🔄 Comparison with similar tools

| Feature | **gh-repo-health** | github-stats | repo-health-check | Codecov |
|---|:---:|:---:|:---:|:---:|
| Zero tokens / zero setup | ✅ | ❌ | ❌ | ❌ |
| Works on any public repo | ✅ | ✅ | ✅ | ✅ |
| Works on private repos | ✅ | ❌ | ❌ | Paid |
| Self-contained HTML report | ✅ | ❌ | ❌ | ❌ |
| Letter grade + breakdown | ✅ | ❌ | ✅ | ❌ |
| Commit streak tracking | ✅ | ✅ | ❌ | ❌ |
| PR cycle time (median) | ✅ | ❌ | ❌ | ❌ |
| Day/hour heatmaps | ✅ | ❌ | ❌ | ❌ |
| JSON export | ✅ | ❌ | ❌ | ✅ |
| Single-file, no install | ✅ | ❌ | ❌ | ❌ |
| Offline after first run | ✅ | ❌ | ❌ | ❌ |

**When to use what:**
- **gh-repo-health** — Solo devs and small teams who want a fast, beautiful, zero-friction snapshot of their repo.
- **github-stats** — If you primarily want a GitHub profile README badge.
- **repo-health-check** — If you're a maintainer focused on OSS best-practice checklists (license, CoC, CI).
- **Codecov** — If code coverage reporting is your primary concern.

---

## 📦 Installation guide

### Prerequisites

**1. Python 3.8+**
```bash
python --version   # should print 3.8 or higher
```
If not installed: [python.org/downloads](https://www.python.org/downloads/)

**2. GitHub CLI (`gh`)**

```bash
# macOS
brew install gh

# Windows (winget)
winget install --id GitHub.cli

# Debian / Ubuntu
sudo apt install gh

# Fedora / RHEL
sudo dnf install gh

# Any platform via conda
conda install -c conda-forge gh
```
Full instructions: [cli.github.com](https://cli.github.com/)

**3. Authenticate**
```bash
gh auth login
# Follow the prompts — browser-based OAuth, takes ~30 seconds
```

### Install gh-repo-health

**Option A — clone (recommended)**
```bash
git clone https://github.com/your-username/gh-repo-health
cd gh-repo-health
pip install rich   # optional but recommended
```

**Option B — single-file curl install**
```bash
curl -O https://raw.githubusercontent.com/your-username/gh-repo-health/main/gh_repo_health.py
pip install rich
```

**Option C — run directly from any repo**
```bash
# From inside any git repo, just point to the script
python /path/to/gh_repo_health.py
```

### Verify it works

```bash
python gh_repo_health.py --repo cli/cli --days 30 --no-browser
# Should print a grade + summary for GitHub's own CLI repo
```

### Troubleshooting

**`gh: command not found`** — Install the GitHub CLI per step 2 above.

**`Not authenticated. Run: gh auth login`** — Run `gh auth login` and follow the prompts.

**`Cannot detect repo. Pass --repo owner/repo`** — You're not inside a git repo. Either `cd` into one or pass `--repo owner/repo` explicitly.

**`Could not fetch commits / PRs / issues`** — You may be rate-limited or the repo requires higher permissions. Try `gh auth status` to verify your token scopes.

---

## 📊 Health score

The dashboard computes a **0–100 health score** (letter grade A–D) from six weighted signals:

```
Commit Velocity    ████████████████████  20 pts  (target: ≥ 5 commits/week)
PR Merge Rate      ████████████████████  20 pts  (target: ≥ 80% merged)
Commit Streak      ███████████████       15 pts  (target: ≥ 14-day streak)
PR Cycle Time      ███████████████       15 pts  (target: ≤ 3 days median)
Issue Close Rate   ███████████████       15 pts  (target: ≥ 70% closed)
Branch Hygiene     ███████████████       15 pts  (fewer stray branches = better)
```

Grades: **A** ≥ 85 · **B** ≥ 70 · **C** ≥ 55 · **D** < 55

Score interpretation:
- **A (85–100)** — Healthy, active project. High velocity, clean PR flow, issues getting closed.
- **B (70–84)** — Good shape. Some areas to tighten up (streaks, branch count, cycle time).
- **C (55–69)** — Needs attention. Velocity may be low or a backlog is growing.
- **D (<55)** — Stalled or neglected. Consider a focused sprint to clear issues and PRs.

---

## 🖼  Report preview

The HTML report includes:

- **Weekly activity sparklines** — commits, PR opens, issue opens over the last 16 weeks
- **Day-of-week heatmap** — when you actually ship code
- **Hour-of-day histogram** — your peak productivity window (UTC)
- **Health score breakdown** — colour-coded progress bars per category
- **Releases table** — tag, name, date, draft/pre-release status
- **Branch inventory** — all non-default branches at a glance
- **Top issue labels** — most active label categories

All charts powered by [Chart.js](https://www.chartjs.org/). No CDN dependencies beyond that — the HTML file is fully self-contained.

---

## 💬 Mention in Python communities

If you find this useful, here are good places to share it:

- [r/Python](https://reddit.com/r/Python) — post under "Showcase" flair with a screenshot of the terminal output
- [r/github](https://reddit.com/r/github) — good fit for the solo-dev angle
- [Hacker News](https://news.ycombinator.com/submit) — "Show HN: gh-repo-health – deep repo analytics for solo devs, zero tokens"
- [Python Discord](https://pythondiscord.com/) — `#project-showcase` channel
- [Real Python community](https://realpython.com/community/) forums

**Suggested post title for HN / Reddit:**
> "gh-repo-health: a single Python file that turns `gh` CLI into a beautiful repo analytics dashboard — no tokens, no API keys"

---

## 📦 Requirements

| Requirement | Notes |
|---|---|
| Python 3.8+ | Standard library only (no extra pip installs required) |
| [gh CLI](https://cli.github.com/) | Authentication handled via `gh auth login` |
| `rich` *(optional)* | `pip install rich` — enables colour terminal output |

No GitHub personal access tokens. No `.env` files. No OAuth apps. `gh` handles all auth.

---

## 🗂  Project structure

```
gh-repo-health/
├── gh_repo_health.py   # single-file tool — everything lives here
├── README.md
└── LICENSE
```

---

## 🤝 Contributing

Issues and PRs welcome. The script is intentionally a single file for easy sharing and `curl`-installation — please keep it that way.

```bash
# Run against this repo itself as a sanity check
python gh_repo_health.py --repo your-username/gh-repo-health --days 30
```

---

## 📄 License

MIT — do whatever you want with it.

---

<div align="center">

Made with `gh`, Python, and an unhealthy obsession with clean dashboards.

**[⬆ back to top](#)**

</div>
