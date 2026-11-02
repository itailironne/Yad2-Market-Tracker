"""Deep audit across every Yad2 data file. Looks for: structural integrity,
field plausibility, date sanity, cross-file consistency, and history coherence.

Run with:  python _audit_all.py
Exits 1 if any FAIL-level issue is found.
"""
import json
import sys
from collections import Counter
from datetime import datetime
import pandas as pd

ENC = "utf-8-sig"
issues = []


def issue(severity, area, msg):
    issues.append((severity, area, msg))


def lid(u):
    return (u or "").split("?")[0].rstrip("/").split("/")[-1]


def exf(info, idx):
    parts = str(info).split(",")
    return parts[idx].strip() if len(parts) > idx else ""


# ── load ──────────────────────────────────────────────────────────────────
with open("yad2_raanana_4rooms.json", encoding="utf-8") as f:
    listings = json.load(f)
with open("yad2_first_seen.json", encoding="utf-8") as f:
    first_seen = json.load(f)
with open("yad2_date_posted.json", encoding="utf-8") as f:
    date_posted = json.load(f)
with open("yad2_prev_run.json", encoding="utf-8") as f:
    prev_run = json.load(f)

hist = pd.read_csv("yad2_history.csv", encoding=ENC)
nb_hist = pd.read_csv("yad2_neighborhood_history.csv", encoding=ENC)
type_hist = pd.read_csv("yad2_type_history.csv", encoding=ENC)
run_log = pd.read_csv("yad2_run_log.csv", encoding=ENC)
dom_log = pd.read_csv("yad2_dom_log.csv", encoding=ENC)
csv_listings = pd.read_csv("yad2_raanana_4rooms.csv", encoding=ENC)


print("=" * 78)
print("  COMPREHENSIVE DATA AUDIT")
print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 78)
print(f"\nListings: JSON={len(listings)} CSV={len(csv_listings)} prev_run={len(prev_run)}")
print(f"first_seen: {len(first_seen)} | date_posted: {len(date_posted)}")
print(f"History rows: history={len(hist)} nb={len(nb_hist)} type={len(type_hist)} run={len(run_log)} dom={len(dom_log)}")


# ── 1. JSON internal consistency ──────────────────────────────────────────
ids = [lid(r.get("url", "")) for r in listings]
dup_ids = [i for i, c in Counter(ids).items() if c > 1]
empty_ids = sum(1 for i in ids if not i)
if dup_ids: issue("FAIL", "json", f"{len(dup_ids)} duplicate listing IDs")
if empty_ids: issue("FAIL", "json", f"{empty_ids} empty/unparseable URLs")
if len(csv_listings) != len(listings):
    issue("FAIL", "json/csv", f"row-count mismatch JSON={len(listings)} CSV={len(csv_listings)}")


# ── 2. Per-listing field sanity ───────────────────────────────────────────
weird_price = weird_rooms = weird_floor = weird_size = 0
size_outliers = []
for r in listings:
    p = str(r.get("price", ""))
    # Real anomaly = price string with no ₪ symbol AND no "no price" sentinel
    if "₪" not in p and "לא צוין" not in p:
        weird_price += 1
    rooms = r.get("rooms")
    # The feed filter is rooms=4-5 (4, 4.5, 5) since 5-room tracking began 2026-07-11
    if rooms not in (None, "") and str(rooms) not in ("4", "4.5", "5"): weird_rooms += 1
    floor = r.get("floor")
    try:
        if floor not in (None, "") and float(floor) > 30: weird_floor += 1
    except Exception:
        pass
    sz = r.get("size_sqm")
    try:
        if sz not in (None, ""):
            sf = float(sz)
            if sf < 30 or sf > 400:
                weird_size += 1
                size_outliers.append((sf, r.get("url", "")))
    except Exception:
        pass

if weird_price: issue("WARN", "price", f"{weird_price} listings without ₪ prefix")
if weird_rooms: issue("FAIL", "rooms", f"{weird_rooms} listings outside 4-5 rooms (feed filter is rooms=4-5)")
if weird_floor: issue("WARN", "floor", f"{weird_floor} listings with floor > 30")
if weird_size:
    issue("WARN", "size_sqm", f"{weird_size} listings outside [30, 400] m²")
    for sz, u in size_outliers[:5]:
        print(f"     size={sz} {u[-40:]}")


# ── 3. Dates ──────────────────────────────────────────────────────────────
today = datetime.now().date()
bad_dp = bad_fs = sat_dp = sat_fs = future_dp = order_v = old_dp = 0
for r in listings:
    dp = (r.get("date_posted") or "")[:10]
    if not dp: continue
    try:
        d = datetime.strptime(dp, "%Y-%m-%d").date()
    except Exception:
        bad_dp += 1
        continue
    if d > today: future_dp += 1
    if d.weekday() == 5: sat_dp += 1
    if d.year < 2018: old_dp += 1
    fs = first_seen.get(lid(r.get("url", "")))
    if fs:
        try:
            fs_d = datetime.strptime(fs[:10], "%Y-%m-%d").date()
            if d > fs_d: order_v += 1
            if fs_d.weekday() == 5: sat_fs += 1
        except Exception:
            bad_fs += 1

if bad_dp: issue("FAIL", "dates", f"{bad_dp} unparseable date_posted")
if sat_dp: issue("FAIL", "dates", f"{sat_dp} date_posted on Saturday")
if sat_fs: issue("FAIL", "dates", f"{sat_fs} first_seen on Saturday")
if future_dp: issue("FAIL", "dates", f"{future_dp} date_posted in the future")
if old_dp: issue("WARN", "dates", f"{old_dp} date_posted before 2018")
if order_v: issue("WARN", "dates", f"{order_v} listings where date_posted > first_seen")


# ── 4. first_seen / date_posted coverage ─────────────────────────────────
active_ids = {lid(r.get("url", "")) for r in listings if lid(r.get("url", ""))}
missing_fs = active_ids - set(first_seen)
missing_dp_listings = sum(1 for r in listings if not r.get("date_posted"))
if missing_fs: issue("FAIL", "first_seen", f"{len(missing_fs)} active listings missing from first_seen.json")
if missing_dp_listings: issue("WARN", "date_posted", f"{missing_dp_listings} listings without any date_posted")


# ── 5. dom_log integrity ──────────────────────────────────────────────────
dup_dom = dom_log.duplicated(subset=["url", "removed_date"]).sum()
dom_log["lid"] = dom_log["url"].astype(str).apply(lid)
ghost_removals = dom_log[dom_log["lid"].isin(active_ids)]
neg_dom = pd.to_numeric(dom_log["dom_days"], errors="coerce").lt(0).sum()
if dup_dom: issue("WARN", "dom_log", f"{int(dup_dom)} dup (url, removed_date) rows (legacy URL-keyed era)")
if len(ghost_removals) > 100:
    issue("WARN", "dom_log", f"{len(ghost_removals)} dom_log rows for IDs that are still active (legacy false-removals)")
if neg_dom: issue("FAIL", "dom_log", f"{int(neg_dom)} rows with dom_days < 0")


# ── 6. history.csv ────────────────────────────────────────────────────────
hist["ts"] = pd.to_datetime(hist["timestamp"])
if not hist["ts"].is_monotonic_increasing:
    issue("WARN", "history", "timestamps not monotonically increasing")
# Saturday timestamps in history files are scraper-run times, not date_posted —
# fine if the scraper happened to run on a Saturday, only flag as info.
zero_count = (hist["count"] == 0).sum()
if zero_count: issue("FAIL", "history", f"{zero_count} rows with count=0")


# ── 7. Latest nb_history vs live ─────────────────────────────────────────
latest_nb_ts = nb_hist["timestamp"].max()
nb_latest = nb_hist[nb_hist["timestamp"] == latest_nb_ts].set_index("neighborhood")["count"].to_dict()
live_nb = Counter()
for r in listings:
    nb = exf(r.get("info", ""), 1)
    if nb:
        # Only count neighborhood if info has 3+ parts (real neighborhood, not city)
        if len(str(r.get("info", "")).split(",")) >= 3:
            live_nb[nb] += 1
nb_mismatches = []
for nb in set(nb_latest) | set(live_nb):
    h, l = int(nb_latest.get(nb, 0)), live_nb.get(nb, 0)
    if h != l:
        nb_mismatches.append((nb, h, l))
if nb_mismatches:
    issue("WARN", "nb_history", f"{len(nb_mismatches)} neighborhoods differ from latest snapshot")


# ── 8. Latest type_history vs live ───────────────────────────────────────
latest_type_ts = type_hist["timestamp"].max()
type_latest = type_hist[type_hist["timestamp"] == latest_type_ts].set_index("apt_type")["count"].to_dict()
live_type = Counter()
for r in listings:
    apt = exf(r.get("info", ""), 0) or "דירה"
    live_type[apt] += 1
type_mismatches = []
for t in set(type_latest) | set(live_type):
    h, l = int(type_latest.get(t, 0)), live_type.get(t, 0)
    if h != l:
        type_mismatches.append((t, h, l))
if type_mismatches:
    issue("WARN", "type_history", f"{len(type_mismatches)} types differ from latest snapshot")


# ── 9. JSON ↔ CSV listing parity ──────────────────────────────────────────
csv_urls = set(csv_listings["url"].tolist()) if "url" in csv_listings.columns else set()
json_urls = {r.get("url", "") for r in listings}
missing_in_csv = json_urls - csv_urls
extra_in_csv = csv_urls - json_urls
if missing_in_csv: issue("WARN", "json/csv", f"{len(missing_in_csv)} JSON URLs missing from CSV")
if extra_in_csv: issue("WARN", "json/csv", f"{len(extra_in_csv)} CSV URLs not in JSON")


# ── 10. run_log sanity ───────────────────────────────────────────────────
status_counts = dict(Counter(run_log["status"]))
err_count = status_counts.get("error", 0)
if err_count >= 3:
    issue("WARN", "run_log", f"{err_count} error runs out of {len(run_log)} ({err_count*100//len(run_log)}%)")


# ── REPORT ───────────────────────────────────────────────────────────────
fails = [(s, a, m) for s, a, m in issues if s == "FAIL"]
warns = [(s, a, m) for s, a, m in issues if s == "WARN"]

print()
print("=" * 78)
print(f"  RESULT: {len(fails)} FAIL  |  {len(warns)} WARN  |  total {len(issues)}")
print("=" * 78)
if fails:
    print("\n  FAIL:")
    for s, a, m in fails:
        print(f"    [{a}] {m}")
if warns:
    print("\n  WARN:")
    for s, a, m in warns:
        print(f"    [{a}] {m}")
if not issues:
    print("\n  Nothing to flag. Data clean.")

sys.exit(1 if fails else 0)
