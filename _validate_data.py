"""Yad2 data integrity validator. Run after the scraper to audit the dataset."""
import csv, json, os, re
from datetime import datetime, timedelta
from collections import Counter

import pandas as pd

DIR = os.path.dirname(os.path.abspath(__file__))


def shift_saturday_to_friday(date_str):
    if not date_str: return date_str
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        if dt.weekday() == 5:
            return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
        return str(date_str)
    except Exception:
        return str(date_str)


def parse_price(p):
    p = str(p).replace(",", "").replace("₪", "").strip()
    m = re.search(r"(\d+)", p)
    return int(m.group(1)) if m else None


def listing_id(url):
    return (url or "").split("?")[0].rstrip("/").split("/")[-1]


# ── Load every file we care about ─────────────────────────────────────────
def load_json(name):
    path = os.path.join(DIR, name)
    if not os.path.exists(path): return None
    with open(path, encoding="utf-8") as f: return json.load(f)


def load_csv(name):
    path = os.path.join(DIR, name)
    if not os.path.exists(path): return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


listings   = load_json("yad2_raanana_4rooms.json") or []
prev_run   = load_json("yad2_prev_run.json") or []
first_seen = load_json("yad2_first_seen.json") or {}
date_post  = load_json("yad2_date_posted.json") or {}
hist       = load_csv("yad2_history.csv")
nb_hist    = load_csv("yad2_neighborhood_history.csv")
type_hist  = load_csv("yad2_type_history.csv")
run_log    = load_csv("yad2_run_log.csv")
dom_log    = load_csv("yad2_dom_log.csv")
csv_listings = load_csv("yad2_raanana_4rooms.csv")

issues = []
sections = []


def section(name, status, summary, details=None):
    sections.append((name, status, summary))
    if details:
        for d in details:
            issues.append(f"[{name}] {d}")


# ── A. Field completeness ─────────────────────────────────────────────────
def check_completeness():
    fields = ["price", "street", "info", "rooms", "floor", "size_sqm", "url", "date_posted"]
    missing = {f: 0 for f in fields}
    no_url = 0
    for r in listings:
        for f in fields:
            if not r.get(f):
                missing[f] += 1
        if not r.get("url"):
            no_url += 1
    bad = [f"{f} missing in {n}/{len(listings)} listings" for f, n in missing.items() if n > 0]
    status = "FAIL" if no_url > 0 else ("WARN" if any(missing[f] > len(listings)*0.05 for f in fields) else "OK")
    summary = f"{len(listings)} listings; {sum(missing.values())} field-misses across {sum(1 for v in missing.values() if v)} fields"
    section("A. Field completeness", status, summary, bad if bad else None)


# ── B. Field plausibility ─────────────────────────────────────────────────
def check_plausibility():
    warns = []
    bounds = {
        "price": (500_000, 20_000_000, lambda r: parse_price(r.get("price"))),
        "size_sqm": (30, 500, lambda r: float(r.get("size_sqm")) if r.get("size_sqm") not in (None, "") else None),
        "rooms": (1, 10, lambda r: float(r.get("rooms")) if r.get("rooms") not in (None, "") else None),
        "floor": (-2, 50, lambda r: float(r.get("floor")) if r.get("floor") not in (None, "") else None),
    }
    for field, (lo, hi, getter) in bounds.items():
        outliers = []
        for r in listings:
            try:
                v = getter(r)
            except Exception:
                v = None
            if v is None: continue
            if v < lo or v > hi:
                outliers.append((r.get("url",""), v))
        if outliers:
            outliers.sort(key=lambda t: t[1])
            warns.append(f"{field}: {len(outliers)} out-of-range — example: {outliers[0][1]} ({outliers[0][0][-30:]})")
            for u, v in outliers[:5]:
                warns.append(f"   · {field}={v}  {u}")
    status = "OK" if not warns else "WARN"
    summary = "no outliers" if not warns else f"{len(warns)} outliers found"
    section("B. Field plausibility", status, summary, warns or None)


# ── C. Date sanity ────────────────────────────────────────────────────────
def check_dates():
    errs = []
    today = datetime.now().date()
    floor_date = datetime(2018, 1, 1).date()
    bad_format = bad_future = bad_old = bad_saturday = bad_order = 0
    for r in listings:
        dp = (r.get("date_posted") or "")[:10]
        url = r.get("url", "")
        if not dp:
            continue
        try:
            d = datetime.strptime(dp, "%Y-%m-%d").date()
        except Exception:
            bad_format += 1
            continue
        if d > today: bad_future += 1
        if d < floor_date: bad_old += 1
        if d.weekday() == 5: bad_saturday += 1
        fs = first_seen.get(listing_id(url))
        if fs:
            try:
                fs_d = datetime.strptime(fs[:10], "%Y-%m-%d").date()
                if d > fs_d:
                    bad_order += 1
            except Exception:
                pass

    if bad_format:    errs.append(f"{bad_format} unparseable date_posted values")
    if bad_future:    errs.append(f"{bad_future} listings with date_posted in the future")
    if bad_old:       errs.append(f"{bad_old} listings with date_posted < 2018")
    if bad_saturday:  errs.append(f"{bad_saturday} listings with date_posted on a SATURDAY (rule violation!)")
    if bad_order:     errs.append(f"{bad_order} listings where date_posted > first_seen")
    status = "FAIL" if (bad_saturday or bad_format) else ("WARN" if errs else "OK")
    summary = "all dates clean" if not errs else f"{sum([bad_format,bad_future,bad_old,bad_saturday,bad_order])} date issues"
    section("C. Date sanity", status, summary, errs or None)


# ── D. URL & cross-file integrity ─────────────────────────────────────────
def check_integrity():
    errs = []
    urls = [r.get("url", "") for r in listings if r.get("url")]
    dup = [u for u, c in Counter(urls).items() if c > 1]
    if dup: errs.append(f"{len(dup)} duplicate URLs in current snapshot")

    # JSON vs CSV row count
    if len(csv_listings) and len(csv_listings) != len(listings):
        errs.append(f"json/csv mismatch: {len(listings)} json vs {len(csv_listings)} csv rows")

    # Active listing-IDs missing from first_seen
    missing_fs = [u for u in urls if listing_id(u) not in first_seen]
    if missing_fs:
        errs.append(f"{len(missing_fs)} active listings not in first_seen.json (sample: {missing_fs[0][-40:]})")

    # Saturday leftovers
    sat_count = 0
    for f in ("yad2_history.csv","yad2_neighborhood_history.csv","yad2_type_history.csv","yad2_run_log.csv","yad2_dom_log.csv"):
        df_ = load_csv(f)
        if len(df_):
            for col in df_.columns:
                if df_[col].dtype == object:
                    sat_count += df_[col].astype(str).str.contains("2026-04-25").sum()
    if sat_count: errs.append(f"{sat_count} cells still contain 2026-04-25 (Saturday)")

    status = "FAIL" if (dup or sat_count) else ("WARN" if errs else "OK")
    summary = "all consistent" if not errs else f"{len(errs)} integrity issues"
    section("D. URL & cross-file integrity", status, summary, errs or None)


# ── E. History consistency ────────────────────────────────────────────────
def check_history():
    errs = []
    if len(hist) == 0:
        section("E. History consistency", "WARN", "history empty", ["yad2_history.csv has 0 rows"])
        return
    last = hist.iloc[-1]
    h_count = int(last.get("count", 0) or 0)
    live_count = len(listings)
    drift = abs(h_count - live_count) / max(live_count, 1) * 100
    if drift > 2:
        errs.append(f"history.last.count={h_count} vs live={live_count} ({drift:.1f}% drift)")
    if "avg_active_dom" not in hist.columns:
        errs.append("avg_active_dom column missing — scraper update not yet run?")
    elif pd.isna(last.get("avg_active_dom")) or str(last.get("avg_active_dom")) in ("", "nan"):
        errs.append("avg_active_dom not populated for latest run")

    if len(run_log) >= 5:
        recent = run_log.tail(5)["status"].value_counts().to_dict()
        if recent.get("error", 0) >= 2:
            errs.append(f"recent run_log shows {recent.get('error',0)} errors in last 5 runs: {recent}")

    status = "FAIL" if drift > 5 else ("WARN" if errs else "OK")
    summary = f"latest history row count={h_count}, live={live_count}"
    section("E. History consistency", status, summary, errs or None)


# ── F. Drift detection ────────────────────────────────────────────────────
def check_drift():
    errs = []
    if len(hist) < 3:
        section("F. Drift detection", "OK", "not enough history yet (<3 runs)", None)
        return
    h = hist.copy()
    h["date"] = pd.to_datetime(h["timestamp"])
    h = h.sort_values("date")
    week = h.tail(14)
    if len(week) >= 2:
        med_count = float(week["count"].median())
        live_count = len(listings)
        if med_count > 0:
            drift = (live_count - med_count) / med_count * 100
            if abs(drift) > 30:
                errs.append(f"listing count {live_count} vs 7d median {med_count:.0f} ({drift:+.1f}%)")
        med_price = float(pd.to_numeric(week["avg_price"], errors="coerce").median())
        live_avg  = sum(parse_price(r.get("price","")) or 0 for r in listings) / max(len(listings),1)
        if med_price > 0:
            pdrift = (live_avg - med_price) / med_price * 100
            if abs(pdrift) > 5:
                errs.append(f"avg price ₪{int(live_avg):,} vs 7d median ₪{int(med_price):,} ({pdrift:+.1f}%)")

    status = "WARN" if errs else "OK"
    summary = "no significant drift" if not errs else "; ".join(errs)
    section("F. Drift detection", status, summary, errs or None)


# ── Run all checks ────────────────────────────────────────────────────────
check_completeness()
check_plausibility()
check_dates()
check_integrity()
check_history()
check_drift()


# ── Print report ──────────────────────────────────────────────────────────
def colour(s):  # ANSI for terminals that support it; harmless otherwise
    if s == "OK":   return f"\033[92m{s}\033[0m"
    if s == "WARN": return f"\033[93m{s}\033[0m"
    if s == "FAIL": return f"\033[91m{s}\033[0m"
    return s


print("=" * 70)
print("  Yad2 Data Integrity Report")
print("  Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 70)
for name, status, summary in sections:
    dots = "." * max(2, 38 - len(name))
    print(f"  {name} {dots} {colour(status):<22}  {summary}")
print()

if issues:
    print("Issues to review:")
    for i in issues:
        print("  -", i)
else:
    print("No issues found.")
print("=" * 70)

# exit non-zero if any FAIL
fail_count = sum(1 for _, s, _ in sections if s == "FAIL")
import sys
sys.exit(1 if fail_count else 0)
