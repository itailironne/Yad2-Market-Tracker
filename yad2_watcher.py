"""Hourly watchdog for the Yad2 scraper.

Reads the latest run-log row and triggers a manual scraper run only if the
last success is stale. Skips when the scraper is already running or when
we're inside the scheduled-task window. Decisions are appended to
yad2_watcher.log so the operator can see what the watcher chose to do.

Designed to be invoked by a Windows scheduled task once per hour; harmless
to call any time.
"""

import csv, os, subprocess, sys
from datetime import datetime

OUT         = os.path.dirname(os.path.abspath(__file__))
# Both legs' run logs. Watching only the sale log made the rent leg's two-week
# freeze structurally invisible: run_all() scrapes sale then rent in one process,
# so a run where sale succeeds and rent fails still refreshes the sale log and
# reads as healthy. Staleness is judged on the WORST leg.
RUN_LOGS    = [os.path.join(OUT, "yad2_run_log.csv"),
               os.path.join(OUT, "yad2_run_log_rent.csv")]
RUN_LOG     = RUN_LOGS[0]
SCRAPER     = os.path.join(OUT, "yad2_scraper.py")
WATCHER_LOG = os.path.join(OUT, "yad2_watcher.log")
SCRAPER_OUT = os.path.join(OUT, "_scraper_run.log")
PYTHON      = sys.executable

STALE_HOURS          = 13
SKIP_WINDOW_MIN      = 20
SCHEDULED_TASK_HOURS = (9, 20)


def log(decision, reason):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(WATCHER_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts}  {decision:<20s}  {reason}\n")


def _leg_success_age_hours(run_log):
    if not os.path.exists(run_log):
        return None
    last_success = None
    with open(run_log, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) >= 2 and row[1] == "success":
                last_success = row[0]
    if not last_success:
        return None
    try:
        dt = datetime.strptime(last_success, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return (datetime.now() - dt).total_seconds() / 3600


def latest_success_age_hours():
    """Age of the STALEST leg, so one healthy leg cannot mask a frozen one.
    Returns None only when no leg has ever logged a success."""
    ages = [a for a in (_leg_success_age_hours(p) for p in RUN_LOGS) if a is not None]
    return max(ages) if ages else None


def per_leg_ages():
    """(name, age) per leg, for the watcher log so a freeze is visible at a glance."""
    return [(os.path.basename(p).replace("yad2_run_log", "").replace(".csv", "") or "sale",
             _leg_success_age_hours(p)) for p in RUN_LOGS]


def scraper_already_running():
    try:
        # @(...) forces an array before .Count. Without it, a SINGLE match returns
        # a bare CimInstance whose type adapter resolves .Count against the WMI
        # object's own properties, not PowerShell's scalar fallback — yielding an
        # empty string, hence 0, hence "no scraper running" in exactly the
        # one-instance case this guard exists to detect.
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -like '*yad2_scraper.py*' }).Count"],
            capture_output=True, text=True, timeout=15
        )
        return int((result.stdout.strip() or "0")) > 0
    except Exception:
        # Fail CLOSED: an unreachable/slow WMI query must not be read as "nothing
        # is running" and license a second concurrent scraper over the same files.
        return True


def in_scheduled_window():
    now = datetime.now()
    for h in SCHEDULED_TASK_HOURS:
        scheduled = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if abs((now - scheduled).total_seconds()) <= SKIP_WINDOW_MIN * 60:
            return h
    return None


def launch_scraper_detached():
    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP — the scraper keeps running
    # after the watcher exits and Task Scheduler sees the watcher as done.
    flags = 0x00000008 | 0x00000200
    # Append, never truncate: a detached scraper from an earlier launch holds its
    # own handle at its own offset, so opening this shared path with "w" wiped a
    # live run's diagnostics (and left the file NUL-padded). The wedged 6.6-day
    # run's entire warm-up trace was lost this way.
    out = open(SCRAPER_OUT, "a", encoding="utf-8")
    out.write(f"\n=== launch {datetime.now():%Y-%m-%d %H:%M:%S} ===\n")
    out.flush()
    subprocess.Popen(
        # -u: unbuffered. Redirected to a file, Python block-buffers stdout, so
        # a healthy run's log stayed empty for its whole duration and looked
        # wedged (2026-10-23: a finished run was nearly killed as "stuck").
        [PYTHON, "-u", SCRAPER],
        stdout=out, stderr=subprocess.STDOUT, cwd=OUT,
        creationflags=flags, close_fds=False,
    )


def main():
    age = latest_success_age_hours()
    if age is not None and age < STALE_HOURS:
        log("skip-fresh", f"last success {age:.1f}h ago (<{STALE_HOURS}h)")
        return

    if scraper_already_running():
        log("skip-in-progress", "scraper python process already active")
        return

    skip_hour = in_scheduled_window()
    if skip_hour is not None:
        log("skip-window", f"within +/-{SKIP_WINDOW_MIN}m of scheduled task {skip_hour:02d}:00")
        return

    age_str = f"{age:.1f}h" if age is not None else "n/a"
    legs = ", ".join(f"{name}={a:.1f}h" if a is not None else f"{name}=never"
                     for name, a in per_leg_ages())
    log("run", f"stalest leg {age_str} ({legs}), triggering scraper")
    launch_scraper_detached()


if __name__ == "__main__":
    main()
