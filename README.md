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
