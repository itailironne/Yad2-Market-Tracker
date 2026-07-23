"""Backfill avg_active_dom column in yad2_history.csv from first_seen + dom_log."""
import os, csv, json, shutil
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(DIR, "yad2_first_seen.json"), encoding="utf-8") as f:
    first_seen = json.load(f)
# Real Yad2 posting date — months/weeks earlier than first_seen for most listings
date_posted_path = os.path.join(DIR, "yad2_date_posted.json")
date_posted = {}
if os.path.exists(date_posted_path):
    with open(date_posted_path, encoding="utf-8") as f:
        date_posted = json.load(f)

# dom_log gives us the removal date for URLs that have been removed
removed_at = {}
dom_log_path = os.path.join(DIR, "yad2_dom_log.csv")
if os.path.exists(dom_log_path):
    with open(dom_log_path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            url = r.get("url", "")
            d   = r.get("removed_date", "")
            if url and d:
                # If the same url was removed multiple times, keep the latest removal
                if url not in removed_at or d > removed_at[url]:
                    removed_at[url] = d

# Use date_posted (real Yad2 posting date) when available; fall back to first_seen
fs_parsed = {}
for url, fs in first_seen.items():
    real_date = date_posted.get(url) or date_posted.get(url.split("?")[0]) or fs
    try:
        fs_parsed[url] = datetime.strptime(str(real_date)[:10], "%Y-%m-%d")
    except Exception:
        pass

rem_parsed = {}
for url, d in removed_at.items():
    try:
        rem_parsed[url] = datetime.strptime(str(d)[:10], "%Y-%m-%d")
    except Exception:
        pass

def avg_active_dom_at(ts_str):
    try:
        T = datetime.strptime(ts_str[:10], "%Y-%m-%d")
    except Exception:
        return ""
    total = 0
    count = 0
    for url, fs in fs_parsed.items():
        if fs > T:
            continue
        rem = rem_parsed.get(url)
        if rem is not None and rem <= T:
            continue
        days = (T - fs).days
        if days < 0:
            continue
        total += days
        count += 1
    return round(total / count, 1) if count else ""

hist_path = os.path.join(DIR, "yad2_history.csv")
shutil.copy2(hist_path, os.path.join(DIR, "_backup_before_saturday_cleanup", "yad2_history.csv.bak2"))

with open(hist_path, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    print("history is empty")
    raise SystemExit

fields = list(rows[0].keys())
if "avg_active_dom" not in fields:
    fields.append("avg_active_dom")

filled = 0
for r in rows:
    # Re-compute even if column already exists (previous backfill used first_seen and gave 0s)
    v = avg_active_dom_at(r.get("timestamp", ""))
    r["avg_active_dom"] = v
    if v != "":
        filled += 1

with open(hist_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"backfilled {filled} rows with avg_active_dom")
