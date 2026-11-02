# AI Setup Guide — Yad2 Market Tracker on a new Windows PC

> **Audience:** an AI coding agent (Claude Code or similar) asked to install,
> verify, or troubleshoot this project on a new machine. The human-oriented
> version of these steps is `MIGRATION.md`; architecture details are in `README.md`.

## 1. What this project is

A personal real-estate tracker for **Ra'anana, Israel, 4–5-room apartments** on
Yad2 (Israel's main listings site). It has two feeds, **sale** and **rent**, and
three Python entry points, all in the project root:

| File | Role | How it runs |
|---|---|---|
| `yad2_scraper.py` | Scrapes both feeds with Playwright + real Chrome, diffs against the previous run, appends history | Scheduled 09:00 & 20:00, plus watcher catch-ups |
| `yad2_watcher.py` | Hourly: if the last successful run is >13h old, launches the scraper | Scheduled hourly |
| `yad2_dashboard.py` | Streamlit dashboard (Hebrew, RTL) at http://localhost:8501 | Manually, via `פתח דשבורד יד2.bat` |

Every script locates its files with `os.path.dirname(os.path.abspath(__file__))`.
**The project folder can live at any path, and no paths need editing.**

## 2. Files: what matters and what doesn't

**Data: never delete, never let two processes write at once.** Sale files are
`yad2_*.csv` / `yad2_*.json`; rent files are the same names with a `_rent`
suffix (e.g. `yad2_history_rent.csv`). The key ones are:

- `yad2_raanana_4rooms[_rent].json/.csv`: current snapshot
- `yad2_prev_run[_rent].json`: baseline for the next diff
- `yad2_first_seen[_rent].json`, `yad2_date_posted[_rent].json`: listing ages (days on market)
- `yad2_history*.csv`, `yad2_*_history*.csv`, `yad2_dom_log*.csv`: append-only time series
- `yad2_listings_archive[_rent].csv`: append-only raw archive (data-loss safety net)
- `yad2_run_log[_rent].csv`: one row per run, `success` or `error` + message
- `yad2_neighborhood_ids.json`: Yad2 neighborhood filter IDs (static)

Some data files are **not tracked in git**, so a `git clone` alone is incomplete.
The whole folder must be copied.

**Machine-local: safe to delete, rebuilt automatically:**

- `.yad2_chrome_profile/`: Chrome profile holding Yad2 anti-bot cookies
- `.yad2_scraper.lock`: single-instance lock (contains the PID)
- `__pycache__/`, `*.log` (`_scraper_run.log`, `yad2_watcher.log`)

**Setup helpers:** `requirements.txt` (pinned), `setup_new_pc.ps1` (installs
packages and registers the scheduled tasks).

## 3. Setup procedure

The environment is Windows 10/11 and PowerShell 5.1: no `&&`, no `??`, and
native stderr redirection is unreliable.

1. **Prerequisites.** Ask the human to install these if they're missing; both
   installers are GUI-based:
   - Python 3.12 from python.org, with the **py launcher** enabled. Check with `py --version`.
   - **Google Chrome**, the real browser. The scraper uses `channel="chrome"`,
     not Playwright's bundled Chromium, so `playwright install` is NOT needed.
2. **Run the setup script** from the project folder:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup_new_pc.ps1
   ```
   It pip-installs `requirements.txt` and registers `Yad2_Morning` (09:00),
   `Yad2_Evening` (20:00) and `Yad2_Watcher` (hourly) for the current user,
   with an **Interactive** logon. It is safe to re-run.
3. **Verify the tasks:**
   ```powershell
   'Yad2_Morning','Yad2_Evening','Yad2_Watcher' | % { Get-ScheduledTask -TaskName $_ | Select TaskName,State }
   ```
4. **Run one scrape in the foreground** and let it finish (10–15 min). It opens
   visible Chrome windows; that is expected.
   ```powershell
   py yad2_scraper.py
   ```
   **Success criteria:** the output contains `[sale] Saved: N listings` (N ≈ 600–950)
   and `[rent] Saved: N listings` (N ≈ 100–160). The last rows of
   `yad2_run_log.csv` and `yad2_run_log_rent.csv` start with today's
   timestamp and `success`.
5. **Start the dashboard:** run `py -m streamlit run yad2_dashboard.py --server.headless true`,
   or double-click the `.bat`. `http://localhost:8501` should return HTTP 200.
6. **Tell the human** to disable or unregister the same three tasks on the OLD PC,
   so the two machines don't both scrape.

## 4. Hard constraints: do not violate

- **The scrape must be headful, in a logged-on desktop session.** Yad2 is
  protected by Radware Bot Manager. Headless Chrome, a spoofed user-agent, or a
  task set to "run whether user is logged on or not" (session 0) will be blocked.
  Keep the tasks on Interactive logon.
- **Only one scraper at a time.** The lock file enforces this. Never delete
  `.yad2_scraper.lock` while its PID is alive. Check with:
  `Get-CimInstance Win32_Process -Filter "Name like 'python%'" | ? CommandLine -match 'yad2_scraper'`
- **A silent log does NOT mean the scraper is hung.** When stdout is redirected
  to a file (as the watcher does into `_scraper_run.log`), Python block-buffers
  the output, so nothing may appear until the run ends. Judge liveness by
  process age (a normal run is under 20 min, or up to ~1.5h with retries) and
  by new rows in the run logs, not by log silence.
- **Do not delete or rewrite data files** to "fix" the dashboard. All filtering
  is display-time: invalid and outlier listings are hidden in `load_current()`
  in `yad2_dashboard.py`, and the raw files keep everything.
- **The scraper's sanity filter and the dashboard's must agree.** If you change
  `min_sane_price` or `min/max_sane_ppsqm` in `SALE_CFG`/`RENT_CFG`
  (`yad2_scraper.py`), mirror the change in `MIN_SANE_PRICE`/`SANE_PPSQM` in
  `yad2_dashboard.py`.

## 5. Troubleshooting map

| Symptom | Likely cause | Action |
|---|---|---|
| Run log: `Radware challenge not cleared` / `Could not obtain Radware clearance` | Fresh Chrome profile or expired cookies | Re-run. On a new PC the first run often needs this. Deleting `.yad2_chrome_profile/` forces a clean warm-up. |
| Run log: `Pagination stopped at page X with N listings (expected >= M)` | Truncated scrape (bot-block), **or** the feed really shrank | Check the page/card counts in `_scraper_run.log`. If the last page is naturally short and N is plausible, Yad2's inventory or page size changed: re-tune `min_listings_for_trust` in `SALE_CFG`/`RENT_CFG` from real data, and update the comment. |
| Run log: `Listing count dropped from A to B ... Refusing to save` | Relative-drop guard (`min_listings_fraction`) | Usually a partial scrape, so retry. If it repeats every run, the baseline may be stale; see `STALE_BASELINE_*` in `yad2_scraper.py`. |
| Run log: `Execution context was destroyed` | The page navigated (bot-check redirect) mid-read | Transient; the next scheduled or watcher run normally succeeds. |
| Dashboard: "updated N days ago", or a red "last run failed" banner | Scrapes failing or not running | Read the last 5 rows of `yad2_run_log*.csv` and the tail of `yad2_watcher.log`. Check that the tasks are `Ready` and that the PC was logged on. |
| Watcher log keeps saying `skip-in-progress` | A scraper process exists (possibly a long run) | Check the process start time before killing it (see the buffering note above). |
| `py` not found in Task Scheduler context | Python installed without the py launcher | Re-install with the launcher, or edit the task Action to the full `python.exe` path. |

**Historical note.** Around 2026-10-07 Yad2 changed from 20 to 50 cards per page.
The old page-count guard (`min_pages_for_trust=25`) then rejected every complete
sale scrape for 16 days. The guard now counts listings. If Yad2 changes its
layout again, check the guards first.

## 6. Conventions when editing this repo

- It is a public portfolio project (GitHub: `itailironne/Yad2-Market-Tracker`).
  Keep commits focused, with clear messages, and keep the README accurate.
- Code comments explain *why*, with measured numbers and dates. Match that style
  when changing thresholds.
- In shell commands, use absolute paths rather than chaining `cd dir && cmd`.
- Ask the human before killing processes, deleting files outside the
  "machine-local" list above, or committing and pushing.
