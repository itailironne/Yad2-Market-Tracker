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
RUN_LOG     = os.path.join(OUT, "yad2_run_log.csv")
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


def latest_success_age_hours():
    if not os.path.exists(RUN_LOG):
        return None
    last_success = None
    with open(RUN_LOG, encoding="utf-8-sig") as f:
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


def scraper_already_running():
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -like '*yad2_scraper.py*' }).Count"],
            capture_output=True, text=True, timeout=15
        )
        return int((result.stdout.strip() or "0")) > 0
    except Exception:
        return False


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
    out = open(SCRAPER_OUT, "w", encoding="utf-8")
    subprocess.Popen(
        [PYTHON, SCRAPER],
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
    log("run", f"last success {age_str}, triggering scraper")
    launch_scraper_detached()


if __name__ == "__main__":
    main()
