"""One-shot cleanup: shift any Saturday-dated entry to the previous Friday across all data files."""
import json, os, csv, shutil
from datetime import datetime, timedelta

DIR = os.path.dirname(os.path.abspath(__file__))

def shift_sat_to_fri(date_str):
    if not date_str: return date_str
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        if dt.weekday() == 5:
            return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
        return str(date_str)
    except Exception:
        return str(date_str)

def is_saturday(date_str):
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        return dt.weekday() == 5
    except Exception:
        return False

# ── Backup folder ────────────────────────────────────────────────────────────
backup = os.path.join(DIR, "_backup_before_saturday_cleanup")
os.makedirs(backup, exist_ok=True)

def backup_file(name):
    src = os.path.join(DIR, name)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(backup, name))
        print(f"  backed up {name}")

# ── 1. JSON files: shift Saturday dates to Friday ────────────────────────────
for fname in ("yad2_first_seen.json", "yad2_date_posted.json"):
    path = os.path.join(DIR, fname)
    if not os.path.exists(path):
        continue
    backup_file(fname)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    shifted = 0
    for k, v in list(data.items()):
        new_v = shift_sat_to_fri(v)
        if new_v != v:
            data[k] = new_v
            shifted += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{fname}: shifted {shifted} Saturday-to-Friday")

# ── 2. CSV files with date columns: shift Saturday dates ─────────────────────
def shift_csv(fname, date_cols):
    path = os.path.join(DIR, fname)
    if not os.path.exists(path):
        return
    backup_file(fname)
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return
    fields = list(rows[0].keys())
    shifted = 0
    for r in rows:
        for col in date_cols:
            if col in r and r[col]:
                new_v = shift_sat_to_fri(r[col])
                if new_v != r[col]:
                    r[col] = new_v
                    shifted += 1
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"{fname}: shifted {shifted} Saturday-to-Friday")

shift_csv("yad2_dom_log.csv", ["removed_date", "first_seen"])

# ── 3. History CSVs: drop rows whose timestamp is on a Saturday ──────────────
def drop_saturdays(fname, ts_col="timestamp"):
    path = os.path.join(DIR, fname)
    if not os.path.exists(path):
        return
    backup_file(fname)
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return
    fields = list(rows[0].keys())
    before = len(rows)
    rows = [r for r in rows if not is_saturday(r.get(ts_col, ""))]
    removed = before - len(rows)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"{fname}: removed {removed} Saturday rows")

drop_saturdays("yad2_history.csv")
drop_saturdays("yad2_neighborhood_history.csv")
drop_saturdays("yad2_type_history.csv")
drop_saturdays("yad2_run_log.csv")

# ── 4. Update current snapshots' date_posted in-place ────────────────────────
for fname in ("yad2_raanana_4rooms.json", "yad2_prev_run.json"):
    path = os.path.join(DIR, fname)
    if not os.path.exists(path):
        continue
    backup_file(fname)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    shifted = 0
    for r in data:
        if r.get("date_posted"):
            new_v = shift_sat_to_fri(r["date_posted"])
            if new_v != r["date_posted"]:
                r["date_posted"] = new_v
                shifted += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"{fname}: shifted {shifted} Saturday-to-Friday")

print("\nDone. Backup of original files in:", backup)
