import asyncio, json, csv, os, re, sys, subprocess, time
from dataclasses import dataclass
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
from collections import Counter, defaultdict

# Force UTF-8 on stdout/stderr so Hebrew prints don't crash under Task Scheduler
# (Windows defaults stdout to cp1252 when there's no attached console).
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

OUT      = os.path.dirname(os.path.abspath(__file__))
CITY_ID  = "8700"   # Ra'anana
ROOMS_QS = "rooms=4-5"

@dataclass(frozen=True)
class DealConfig:
    """Everything that differs between the two Yad2 feeds we track (for-sale
    vs. rental). Sale and rent are separate feeds requiring independent
    pagination/scraping — not a value-split of one feed the way the 4-vs-5
    room bucket is — so each gets its own full set of output files. Rent
    prices are ~100-1000x smaller than sale prices (₪ thousands/month vs ₪
    millions), so min_sane_price/min_listings_for_trust must differ per leg too
    or rent data gets filtered out entirely / false-flagged as a bot-block."""
    key: str                    # "sale" | "rent" — used in prints/logs
    feed_path: str              # "forsale" | "rent" — Yad2 URL path segment
    url: str
    json_file: str
    csv_file: str
    archive_file: str
    history_file: str
    prev_file: str
    display_prev_file: str
    first_seen_file: str
    date_posted_file: str
    date_unverified_file: str   # IDs whose date_posted is a first_seen guess, re-fetched each run
    pending_removals_file: str
    dom_log_file: str
    nb_history_file: str
    type_history_file: str
    rooms_history_file: str
    run_log_file: str
    min_listings_for_trust: int # truncated-pagination floor (raw cards), see SALE/RENT_CFG
    min_sane_price: int         # stats/display outlier floor, see SALE/RENT_CFG
    min_sane_ppsqm: float       # stats/display ₪-per-m² band, see SALE/RENT_CFG
    max_sane_ppsqm: float       # (absolute price alone cannot separate a junk
                                #  listing from a real luxury one — only ₪/m² can)
    min_listings_fraction: float  # partial-scrape floor vs. previous run; MUST be
                                  # per-leg — a small, shrinking feed like rent
                                  # trips a sale-calibrated threshold every run

def _rent_name(base_filename):
    root, ext = os.path.splitext(base_filename)
    return f"{root}_rent{ext}"

SALE_CFG = DealConfig(
    key="sale", feed_path="forsale",
    url=f"https://www.yad2.co.il/realestate/forsale?city={CITY_ID}&{ROOMS_QS}",
    json_file=os.path.join(OUT, "yad2_raanana_4rooms.json"),
    csv_file=os.path.join(OUT, "yad2_raanana_4rooms.csv"),
    archive_file=os.path.join(OUT, "yad2_listings_archive.csv"),
    history_file=os.path.join(OUT, "yad2_history.csv"),
    prev_file=os.path.join(OUT, "yad2_prev_run.json"),
    display_prev_file=os.path.join(OUT, "yad2_prev_display.json"),
    first_seen_file=os.path.join(OUT, "yad2_first_seen.json"),
    date_posted_file=os.path.join(OUT, "yad2_date_posted.json"),
    date_unverified_file=os.path.join(OUT, "yad2_date_unverified.json"),
    pending_removals_file=os.path.join(OUT, "yad2_pending_removals.json"),
    dom_log_file=os.path.join(OUT, "yad2_dom_log.csv"),
    nb_history_file=os.path.join(OUT, "yad2_neighborhood_history.csv"),
    type_history_file=os.path.join(OUT, "yad2_type_history.csv"),
    rooms_history_file=os.path.join(OUT, "yad2_rooms_history.csv"),
    run_log_file=os.path.join(OUT, "yad2_run_log.csv"),
    # Counted in raw listings, NOT pages: on ~2026-10-07 Yad2 went from 20 to 50
    # cards per page, so a complete sale feed (~950 raw) now ends at page 19.
    # The old `min_pages_for_trust=25` (tuned on 20-card pages: healthy runs hit
    # 33-38) rejected every complete scrape as a "bot-block" and froze the sale
    # leg for 16 days. Healthy runs yield 660-950 raw listings; the one known
    # truncation (2026-09-25) yielded 370. 500 rejects that and passes the rest,
    # regardless of page size. Relative drops are caught later by
    # min_listings_fraction.
    min_listings_for_trust=500,
    # Sale asking prices are always well above this; anything lower is a
    # data-entry typo (e.g. a ₪12,700 "price"), not a real listing.
    min_sane_price=500_000,
    # The absolute floor above cannot catch everything: ₪590,000/95 m² and
    # ₪680,000/100 m² listings clear it while sitting at ~₪6,200-6,800/m²
    # against a ~₪28,000/m² market. Raising the floor is not an option — it
    # would delete real luxury stock (₪21M/600 m² is a legitimate ₪35,000/m²).
    # ₪/m² is the only measure that separates the two. Observed on 2026-09-01:
    # junk tops out at 6,800/m², the cheapest genuine listing is 13,462/m²
    # (₪7M, 520 m² house), and the dearest genuine is 54,632/m². The band
    # below sits in that gap with headroom on both sides.
    min_sane_ppsqm=10_000,
    max_sane_ppsqm=100_000,
    # Sale's feed is large (~690) and stable, so a >10% drop really is suspicious.
    # This is the value the guard was originally tuned to on 2026-05-17.
    min_listings_fraction=0.9,
)

RENT_CFG = DealConfig(
    key="rent", feed_path="rent",
    url=f"https://www.yad2.co.il/realestate/rent?city={CITY_ID}&{ROOMS_QS}",
    json_file=os.path.join(OUT, _rent_name("yad2_raanana_4rooms.json")),
    csv_file=os.path.join(OUT, _rent_name("yad2_raanana_4rooms.csv")),
    archive_file=os.path.join(OUT, _rent_name("yad2_listings_archive.csv")),
    history_file=os.path.join(OUT, _rent_name("yad2_history.csv")),
    prev_file=os.path.join(OUT, _rent_name("yad2_prev_run.json")),
    display_prev_file=os.path.join(OUT, _rent_name("yad2_prev_display.json")),
    first_seen_file=os.path.join(OUT, _rent_name("yad2_first_seen.json")),
    date_posted_file=os.path.join(OUT, _rent_name("yad2_date_posted.json")),
    date_unverified_file=os.path.join(OUT, _rent_name("yad2_date_unverified.json")),
    pending_removals_file=os.path.join(OUT, _rent_name("yad2_pending_removals.json")),
    dom_log_file=os.path.join(OUT, _rent_name("yad2_dom_log.csv")),
    nb_history_file=os.path.join(OUT, _rent_name("yad2_neighborhood_history.csv")),
    type_history_file=os.path.join(OUT, _rent_name("yad2_type_history.csv")),
    rooms_history_file=os.path.join(OUT, _rent_name("yad2_rooms_history.csv")),
    run_log_file=os.path.join(OUT, _rent_name("yad2_run_log.csv")),
    # Ra'anana's 4-5-room rental inventory is much smaller than sale's:
    # _probe_rent_feed.py measured 8 real pages (vs sale's 20+). Threshold set
    # with headroom below that for normal day-to-day inventory dips (reusing
    # sale's threshold of 10 here would make every healthy rent run look like
    # a bot-block, since rent never reaches 10 pages at all).
    # Rent's inventory is ~4x smaller than sale's and shrinking (201 -> 143 over
    # Sep-Oct). Measured over 39 successful runs, 23 of them land at pnum=5 —
    # EXACTLY the old threshold of 5, i.e. zero headroom: the guard passes only
    # because `5 < 5` is false. Lose one page of inventory and every healthy rent
    # run starts failing as a false bot-block. 3 keeps real protection (a genuine
    # block dies on page 1-2) while leaving room for the feed to keep shrinking.
    # The comment that justified 5 cited a _probe_rent_feed.py that doesn't exist.
    # Since Yad2's move to 50-card pages the ~138-listing rent feed is exactly 3
    # pages, back to zero headroom — so this is now a listing count, like sale's.
    # A genuine block dies on page 1 (<= 50 raw); 60 rejects that, and
    # min_listings_fraction (0.75) covers a truncation further in.
    min_listings_for_trust=60,
    # Placeholder — real 4-5 room monthly rent in Ra'anana is roughly
    # ₪3,000-15,000. Re-tune after seeing real scraped data.
    min_sane_price=1_500,
    # Deliberately LOOSE, unlike sale. Rent has no junk/genuine gap to exploit:
    # monthly rent does not scale with floor area, so the cheapest ₪/m² entries
    # (₪5,000 for 250 m², = ₪20/m²) are real houses, not typos. Observed range
    # on the 2026-08-18 snapshot was 20-144/m². These bounds are guard-rails
    # against a mis-keyed digit only; tightening them would delete real stock.
    min_sane_ppsqm=10,
    max_sane_ppsqm=500,
    # Rent's feed is ~4x smaller (176 vs ~690) and has been shrinking steadily
    # (192 -> 191 -> 188 -> 176 over Aug), so the same 10% drop that would be
    # alarming for sale is ordinary month-to-month movement here. Sale's 0.9
    # demanded >=158 listings against a frozen 176 baseline and rejected every
    # rent run for two weeks straight.
    min_listings_fraction=0.75,
)
DEAL_CONFIGS = [SALE_CFG, RENT_CFG]

# Dedicated Chrome profile that holds Radware Bot-Manager clearance cookies.
# Warmed by a genuine (non-automated) Chrome before every run, then reused by
# Playwright — see warm_clearance() and the launch_persistent_context() call.
# Shared across both legs: clearance cookies are domain-level (yad2.co.il),
# not path-specific, so warming once (on the sale URL) also clears the rent
# path — no need to pay the ~40s+ visible-Chrome warm-up twice.
PROFILE_DIR       = os.path.join(OUT, ".yad2_chrome_profile")
# Single-instance lock. The scraper is launched from three places (the 09:00/
# 20:00 scheduled tasks, the hourly watchdog, and manual runs). Two runs at once
# would fight over PROFILE_DIR (a Chrome profile allows only one live process)
# and clobber each other's output files, so only one may hold this lock.
LOCK_FILE         = os.path.join(OUT, ".yad2_scraper.lock")

# Baseline-age escape hatch for the partial-scrape guard (cfg.min_listings_fraction).
# The fraction assumes the normal ~12h cadence, where a 10% drop really is
# anomalous. After a multi-day gap the comparison is no longer "daily churn" and
# the guard can no longer tell a partial scrape from genuine turnover. Worse, a
# rejected run never updates the baseline, so a stale baseline latches the guard
# ON permanently — that ratchet froze the rent leg from 2026-08-18 to 2026-09-01
# (baseline stuck at 176, every later run measured against it and refused).
# Past this age we fall back to a looser floor that still catches a catastrophic
# partial scrape without demanding week-old inventory levels.
#
# 0.5 was TOO LOOSE and caused a regression: the 2026-09-25 07:28 run captured
# only 17 pages / 370 listings against a 43h-old baseline of 711 (52%), cleared
# the relaxed 50% floor, saved, and falsely retired 33 listings. The whole point
# of this guard is to stop exactly that. 0.5 was never needed either — the rent
# ratchet it was written for sat at 157/176 = 89.2%, which clears 0.75 on its
# own. Keep the relaxation meaningful but never permissive enough to admit a
# half-captured feed.
STALE_BASELINE_HOURS    = 36
STALE_BASELINE_FRACTION = 0.75
# Yad2's feed is unstable — boosted/promoted listings flap in and out between
# runs, so a listing simply missing from ONE run is often still live (verified:
# a listing absent from a scrape was confirmed active on yad2 minutes later).
# Require this many CONSECUTIVE absent runs before logging a removal; any
# reappearance cancels the pending removal. Kills false "removed" events that
# were inflating the removed/absorption/DOM stats.
REMOVAL_GRACE_RUNS = 2
# ...but runs alone are the wrong unit. The watcher can fire several times an
# hour, so two misses can span 30 minutes and confirm a "removal" for a listing
# that was merely missed twice by a slow-rendering page. Measured over 13
# archived snapshots, 116 listings were absent for 2+ consecutive runs and later
# came back — every one of them would have been logged as removed. Demand BOTH
# thresholds: N consecutive misses AND this much wall-clock since the first one.
REMOVAL_GRACE_HOURS = 24

def parse_price_num(p):
    p = str(p).replace(",","").replace("\u20aa","").replace("\u20aa","").strip()
    m = re.search(r"(\d+)", p)
    return int(m.group(1)) if m else None

def rooms_bucket(val):
    """Map a listing's room count to the dashboard's two buckets: '4' (4 or 4.5
    rooms) or '5' (5+ rooms). Returns '' for anything outside the scrape filter."""
    try:
        n = float(val)
    except (TypeError, ValueError):
        return ""
    if n >= 5:   return "5"
    if n >= 4:   return "4"
    return ""

def shift_saturday_to_friday(date_str):
    """If date_str (YYYY-MM-DD) falls on Saturday, return the previous Friday instead."""
    if not date_str:
        return date_str
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt.weekday() == 5:  # 5 = Saturday
            return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
        return date_str
    except Exception:
        return date_str

def parse_yad2_date(text):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", str(text))
    if not m: return ""
    d, mo, y = m.groups()
    if len(y) == 2: y = "20" + y
    try:
        result = datetime.strptime(f"{d}/{mo}/{y}", "%d/%m/%Y").strftime("%Y-%m-%d")
        return shift_saturday_to_friday(result)
    except:
        return ""

def extract_id_from_url(url):
    """Extract listing ID from a Yad2 URL like .../item/ABC123.
    Same listing keeps a stable ID across runs even though yad2 randomizes the
    query string (?pagination=…&spot=…&location=…) on every page load."""
    clean = (url or "").split("?")[0].rstrip("/")
    parts = clean.split("/")
    return parts[-1] if parts else ""

def extract_dates_from_json(obj, result, depth=0):
    """Recursively scan API JSON for {id/token: ..., date: ...} objects."""
    if depth > 10:
        return
    if isinstance(obj, dict):
        item_id = obj.get("token") or obj.get("id") or obj.get("orderId")
        for date_key in ("date", "date_added", "date_updated", "publishDate",
                         "feed_date", "updated_at", "created_at", "postedAt"):
            raw = obj.get(date_key)
            if item_id and raw:
                parsed = ""
                if isinstance(raw, str):
                    parsed = parse_yad2_date(raw)
                    if not parsed:
                        try:
                            parsed = datetime.fromtimestamp(int(raw)).strftime("%Y-%m-%d")
                        except:
                            pass
                elif isinstance(raw, (int, float)) and raw > 1_000_000_000:
                    try:
                        parsed = datetime.fromtimestamp(raw).strftime("%Y-%m-%d")
                    except:
                        pass
                if parsed:
                    result[str(item_id)] = parsed
        for v in obj.values():
            extract_dates_from_json(v, result, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            extract_dates_from_json(item, result, depth + 1)

def extract_neighborhood(info):
    """yad2 includes the neighborhood as the 2nd comma-part for most listings:
        "דירה, נווה זמר, רעננה" → "נווה זמר"
    Some cards omit it ("דירה, רעננה") — those return "" here, and then get a
    chance to be enriched via the street→neighborhood lookup built per-run."""
    parts = str(info).split(",")
    if len(parts) >= 3:
        return parts[1].strip()
    return ""


def enrich_missing_neighborhoods(listings):
    """yad2 omits the neighborhood from ~25% of listing cards (info reads
    "דירה, רעננה" with no neighborhood between them). The same street usually
    appears in OTHER listings that DO carry the neighborhood, so we build a
    street→neighborhood lookup from the tagged listings in this run and use it
    to infer the missing neighborhood for the untagged ones.

    Only enriches when a street maps to a single neighborhood across the run
    (avoids guessing on the rare cross-neighborhood streets).

    Mutates each enriched listing's `info` from "דירה, רעננה" to
    "דירה, <neighborhood>, רעננה" so downstream dashboards/aggregations pick
    it up with no further changes. Returns (enriched_count, ambiguous_streets).
    """
    from collections import Counter, defaultdict
    street_to_nbs = defaultdict(Counter)
    for r in listings:
        parts = str(r.get("info", "")).split(",")
        if len(parts) >= 3:
            nb = parts[1].strip()
            street = (r.get("street") or "").strip()
            if street and nb and street != "דירה":
                street_to_nbs[street][nb] += 1
    consistent = {s: list(nbs)[0] for s, nbs in street_to_nbs.items() if len(nbs) == 1}
    ambiguous  = {s for s, nbs in street_to_nbs.items() if len(nbs) > 1}

    enriched = 0
    for r in listings:
        info = str(r.get("info", ""))
        parts = info.split(",")
        if len(parts) >= 3:
            continue  # already has a neighborhood
        street = (r.get("street") or "").strip()
        nb = consistent.get(street)
        if not nb:
            continue
        # Rebuild as "<type>, <nb>, <city>"
        apt_type = parts[0].strip() if parts else "דירה"
        city     = parts[1].strip() if len(parts) >= 2 else "רעננה"
        r["info"] = f"{apt_type}, {nb}, {city}"
        enriched += 1
    return enriched, ambiguous

async def collect_listing_ids_from_url(pg, base_url):
    """Navigate base_url and harvest listing-IDs across all pages. Reuses the
    main scrape's robust click logic so a covered next-page button doesn't
    abort the harvest. Used for per-neighborhood enrichment."""
    ids = set()
    try:
        await pg.goto(base_url, timeout=60000, wait_until="domcontentloaded")
    except Exception:
        return ids
    await pg.wait_for_timeout(2500)
    while True:
        cards = await pg.query_selector_all("[class*=feedItemBox]")
        for c in cards:
            try:
                link_el = await c.query_selector("a[href]")
                if not link_el:
                    continue
                href = await link_el.get_attribute("href") or ""
                url = "https://www.yad2.co.il" + href if href.startswith("/") else href
                if "/realestate/item/" not in url:
                    continue
                lid = extract_id_from_url(url)
                if lid:
                    ids.add(lid)
            except Exception:
                continue
        nb = await pg.query_selector("a[aria-label='עמוד הבא']")
        if not nb or await nb.get_attribute("aria-disabled") == "true":
            break
        clicked = False
        try:
            await nb.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        try:
            await nb.click(timeout=8000)
            clicked = True
        except Exception:
            try:
                await pg.evaluate("(el) => el.click()", nb)
                clicked = True
            except Exception:
                pass
        if not clicked:
            break
        await pg.wait_for_timeout(2500)
    return ids


def ensure_csv_columns(path, expected_cols):
    """If `path` exists and is missing any of `expected_cols`, append the missing columns
    (with empty values for historical rows) so new writes line up with the header."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return
        rows = list(reader)
    missing = [c for c in expected_cols if c not in header]
    if not missing:
        return
    new_header = header + missing
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(new_header)
        for row in rows:
            w.writerow(row + [""] * len(missing))

# ── Radware Bot-Manager clearance ─────────────────────────────────────────────
# Yad2 sits behind Radware Bot Manager (the "stormcaster" script). A cold
# Playwright/CDP browser is served a "Radware Page" JS-challenge that never
# clears, so pagination dies on page 1 ("expected >= 10 pages; likely bot-block").
# A *genuine* Chrome, however, solves that challenge automatically (no CAPTCHA)
# and deposits clearance cookies (__uzm*/uzmx) into its profile. So we warm a
# dedicated profile with a real, visible Chrome first, then let Playwright reuse
# that same profile — it inherits the clearance and scrapes normally.
CHROME_CANDIDATES = [
    os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                 r"Google\Chrome\Application\chrome.exe"),
    os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                 r"Google\Chrome\Application\chrome.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""),
                 r"Google\Chrome\Application\chrome.exe"),
]

def find_chrome_exe():
    for path in CHROME_CANDIDATES:
        if path and os.path.exists(path):
            return path
    return None

def _scraper_process_alive(pid):
    """True only if `pid` is a live process running THIS scraper. We check the
    command line, not just that *some* process has this PID, because PIDs get
    recycled: a crashed scraper's PID can be reused by an unrelated process (e.g.
    the Streamlit dashboard), which would otherwise make the stale lock look
    permanently held and silently block every scheduled/watchdog run."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
            capture_output=True, text=True, timeout=15).stdout
        return "yad2_scraper" in out.lower()
    except Exception:
        return False  # can't confirm a live scraper → let the caller steal the lock

def acquire_single_instance_lock():
    """Return True if we now hold the run lock, False if another live scraper
    already does. A crashed run leaves a stale lock (PID no longer alive); we
    detect that and steal it."""
    try:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            with open(LOCK_FILE) as f:
                pid = int((f.read().strip() or "0"))
        except Exception:
            pid = 0
        if pid and pid != os.getpid() and _scraper_process_alive(pid):
            return False
        try:
            os.remove(LOCK_FILE)                       # stale lock — reclaim it
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            return False
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    return True

def release_single_instance_lock():
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass

def warm_clearance(url, wait_s=40):
    """Launch a genuine, VISIBLE Chrome on PROFILE_DIR so Radware's JS challenge
    solves itself and clearance cookies land in the profile, then kill it so the
    profile is free for Playwright to reuse.

    Must be visible and on-screen: the challenge checks page visibility, so an
    off-screen or minimized window does not clear. A fresh-profile challenge can
    need ~40s to solve; ensure_radware_clearance() re-warms with more time if a
    given warm didn't take. No-op with a warning if Chrome isn't found."""
    exe = find_chrome_exe()
    if not exe:
        print("  WARN: genuine Chrome not found; cannot warm Radware clearance.")
        return
    print(f"  Warming Radware clearance via genuine Chrome ({wait_s}s)...")
    proc = subprocess.Popen([
        exe, f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run", "--no-default-browser-check",
        "--new-window", url,
    ])
    try:
        time.sleep(wait_s)
    finally:
        # Kill the whole process tree (Chrome spawns child renderers) so the
        # profile lock is released before Playwright opens the same dir.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True)
        time.sleep(3)


async def _launch_profile_context(p):
    """Open the warmed Chrome profile with Playwright. channel="chrome" drives
    the real installed Chrome (matching UA + client hints) rather than
    Playwright's bundled Chromium; headful is required because headless Chrome is
    re-fingerprinted and re-challenged even with valid clearance cookies. We
    deliberately do NOT override user_agent — a spoofed UA that contradicts the
    browser's client hints is itself a bot signal (the old Chrome/124 UA was one
    reason detection tightened)."""
    context = await p.chromium.launch_persistent_context(
        PROFILE_DIR,
        channel="chrome",
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ],
        locale="he-IL", timezone_id="Asia/Jerusalem",
        viewport={"width": 1360, "height": 900},
    )
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    )
    return context


async def ensure_radware_clearance(p, url, warm_waits=(40, 55, 70)):
    """Warm the profile with a genuine Chrome and confirm the clearance actually
    took before the real scrape starts. A fresh-profile Radware challenge is
    non-deterministic — one warm occasionally isn't enough — so we verify with a
    throwaway context and re-warm (longer each time) until the feed renders.
    Raises if it never clears, letting the caller back off and try later.

    Clearance cookies are domain-level (yad2.co.il), not path-specific, so
    warming against ANY yad2 URL (typically the sale feed) also clears every
    other path — callers don't need to re-warm per deal type."""
    for attempt, wait_s in enumerate(warm_waits, 1):
        warm_clearance(url, wait_s=wait_s)
        try:
            ctx = await _launch_profile_context(p)
        except Exception as e:
            # Chrome itself failed to launch (e.g. a contended/stale profile
            # lock right after a prior crash) — this used to abort the whole
            # run immediately with no retry. Treat it like "still blocked"
            # instead: fall through to the next warm attempt.
            print(f"  Browser launch failed on warm attempt {attempt}/{len(warm_waits)}: {e}")
            continue
        cleared = False
        try:
            pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await pg.goto(url, timeout=60000, wait_until="domcontentloaded")
            try:
                await pg.wait_for_selector("[class*=feedItemBox]", timeout=15000)
            except Exception:
                pass
            cleared = "Radware" not in (await pg.title())
        finally:
            await ctx.close()
        if cleared:
            print(f"  Radware clearance confirmed (warm attempt {attempt}/{len(warm_waits)}).")
            return
        print(f"  Radware still blocking after warm attempt {attempt}/{len(warm_waits)}; re-warming...")
    raise RuntimeError(
        "Could not obtain Radware clearance after repeated warm-ups; will retry."
    )


# Feed pages lazy-render their cards, so how many exist in the DOM depends on
# network/CPU luck at the instant we look. Reading after a fixed sleep captured
# 5-17 cards on pages whose median yield is 20 — silently dropping ~40-60
# listings per run at random. Measured over 13 archived snapshots: every run had
# 3-11 pages yielding under 18 cards, run-to-run counts swung +/-10%, and 447 of
# 920 distinct listings (48.6%) vanished for a run and came back. Those gaps
# feed REMOVAL_GRACE_RUNS=2 and get confirmed as real removals, so the noise
# reaches the removed/new charts and DOM, not just the count.
CARD_SELECTOR       = "[class*=feedItemBox]"
CARD_SETTLE_POLL_MS = 400    # gap between count probes
CARD_SETTLE_STABLE  = 3      # consecutive equal counts that mean "done rendering"
CARD_SETTLE_MAX_MS  = 12000  # ceiling, so a broken page can't stall the run
CARD_COUNT_WARN     = 45     # full pages hold 50 (20 before ~2026-10-07); fewer => log it

async def settle_card_count(pg):
    """Block until the feed's card count stops growing, then return it.

    Replaces a fixed `wait_for_timeout`: we poll the card count and only proceed
    once it has held steady across CARD_SETTLE_STABLE consecutive probes, giving
    slow pages the time they need while fast ones cost barely more than before.
    Returns the final count so the caller can flag a page that came up short."""
    stable, last, waited = 0, -1, 0
    while waited < CARD_SETTLE_MAX_MS:
        n = len(await pg.query_selector_all(CARD_SELECTOR))
        if n > 0 and n == last:
            stable += 1
            if stable >= CARD_SETTLE_STABLE:
                return n
        else:
            stable = 0
        last = n
        await pg.wait_for_timeout(CARD_SETTLE_POLL_MS)
        waited += CARD_SETTLE_POLL_MS
    return last if last > 0 else 0


async def run_leg(p, cfg, first_seen, today):
    """Scrape one deal-type leg (sale or rent) via the already-warmed shared
    Playwright driver `p`. Opens/closes its own browser context so no
    response-listener/page state bleeds into the other leg. Returns
    (listings, pnum) — does not touch any output file; see finalize_leg()
    for the diff/stats/save step. May raise (bot-block, click failure) —
    the caller (run_leg_with_retry) handles retry/backoff."""
    # Reuse the shared warmed profile for the actual scrape.
    context = await _launch_profile_context(p)
    pg = context.pages[0] if context.pages else await context.new_page()
    listings = []
    seen_urls = set()
    pnum = 1
    intercepted_dates = {}  # listing_id -> date_str

    # ── Intercept API responses to capture dates during feed load ─────────
    async def _on_response(response):
        if response.status != 200:
            return
        if "yad2.co.il" not in response.url:
            return
        if "json" not in response.headers.get("content-type", ""):
            return
        try:
            body = await response.json()
            extract_dates_from_json(body, intercepted_dates)
        except Exception:
            pass
    pg.on("response", _on_response)

    print(datetime.now().strftime("%Y-%m-%d %H:%M"), f"- Starting Yad2 {cfg.key} scrape...")
    await pg.goto(cfg.url, timeout=60000, wait_until="domcontentloaded")
    # Wait for the feed to render, then confirm Radware clearance held. If the
    # warm-up cookies expired or failed we stay on the "Radware Page" challenge
    # with no cards — fail fast so run_leg_with_retry re-warms and retries
    # instead of silently "stopping at page 1" and saving a partial snapshot.
    try:
        await pg.wait_for_selector("[class*=feedItemBox]", timeout=15000)
    except Exception:
        pass
    if "Radware" in (await pg.title()):
        await context.close()
        raise RuntimeError(
            f"[{cfg.key}] Radware challenge not cleared after warm-up (still on "
            f"challenge page); will retry with a fresh warm."
        )
    while True:
        # Wait for the cards to finish rendering rather than sleeping a fixed
        # 2s and reading whatever happens to be there (see settle_card_count).
        n_cards = await settle_card_count(pg)
        if n_cards < CARD_COUNT_WARN:
            print(f"  Page {pnum}: only {n_cards} cards after settle "
                  f"(full page = 50) — possible partial render")
        else:
            print(f"  Page {pnum}: {n_cards} cards")

        # Extract dates from React fiber state on this page (zero extra requests)
        try:
            fiber_dates = await pg.evaluate("""() => {
                const results = {};
                document.querySelectorAll("[class*='feedItemBox']").forEach(card => {
                    const fk = Object.keys(card).find(k => k.startsWith('__reactFiber'));
                    if (!fk) return;
                    let fiber = card[fk];
                    for (let i = 0; i < 50 && fiber; i++) {
                        try {
                            const p = fiber.memoizedProps || {};
                            const src = [p, p.data, p.listing, p.item, p.feedItem, p.adData].filter(Boolean);
                            for (const obj of src) {
                                const id = obj.token || obj.id || obj.orderId;
                                const dt = obj.date || obj.date_added || obj.publishDate ||
                                           obj.feedDate || obj.listingDate || obj.postedAt ||
                                           obj.created_at || obj.updated_at;
                                if (id && dt) { results[String(id)] = String(dt); break; }
                            }
                        } catch(e) {}
                        fiber = fiber.return;
                    }
                });
                return results;
            }""")
            intercepted_dates.update(fiber_dates or {})
        except:
            pass

        cards = await pg.query_selector_all("[class*=feedItemBox]")
        for c in cards:
            try:
                price_el  = await c.query_selector("[data-testid=price]")
                street_el = await c.query_selector("[data-testid=street-name]")
                line1_el  = await c.query_selector("[data-testid=item-info-line-1st]")
                line2_el  = await c.query_selector("[data-testid=item-info-line-2nd]")
                link_el   = await c.query_selector("a[href]")
                price  = (await price_el.inner_text()).strip() if price_el else ""
                street = (await street_el.inner_text()).strip() if street_el else ""
                line1  = (await line1_el.inner_text()).strip() if line1_el else ""
                line2  = (await line2_el.inner_text()).strip() if line2_el else ""
                href   = await link_el.get_attribute("href") if link_el else ""
                card_text = (await c.inner_text()).strip()
                date_posted = parse_yad2_date(card_text)
                url    = "https://www.yad2.co.il" + href if href and href.startswith("/") else href
                # Skip promoted widget blocks ("ListingPro") that aren't real listings
                if not url or "/realestate/item/" not in url:
                    continue
                if url in seen_urls: continue
                seen_urls.add(url)
                rooms = floor = size = ""
                m = re.search(r"(\d+(?:\.\d+)?)\s*\u05d7\u05d3\u05e8", line2)
                if m: rooms = m.group(1)
                # Ground floor: yad2 writes "\u05e7\u05d5\u05de\u05d4 \u05e7\u05e8\u05e7\u05e2" (the word, not a digit),
                # so map it to "0" before the digit regex \u2014 otherwise the regex
                # skips past "\u05e7\u05e8\u05e7\u05e2" and grabs the sqm, which the guard below then
                # blanks, leaving ground-floor flats with no floor at all.
                if re.search(r"\u05e7\u05d5\u05de\u05d4[\s\u200e\u200f]*\u05e7\u05e8\u05e7\u05e2", line2):
                    floor = "0"
                else:
                    m = re.search(r"\u05e7\u05d5\u05de\u05d4[^\d]*(\d+)", line2)
                    if m: floor = m.group(1)
                m = re.search(r"(\d+)\s*\u05de\u05f4\u05e8", line2)
                if m: size = m.group(1)
                # If the "floor" we captured equals the size, the listing actually has no
                # floor number (e.g. garden/penthouse) and the regex jumped to the sqm.
                if floor and floor == size:
                    floor = ""
                # Require both a price AND a street so promoted/empty cards are dropped
                if price and street:
                    listings.append({"price":price,"street":street,"info":line1,"rooms":rooms,"floor":floor,"size_sqm":size,"url":url,"date_posted":date_posted})
            except: continue
        nb = await pg.query_selector("a[aria-label='\u05e2\u05de\u05d5\u05d3 \u05d4\u05d1\u05d0']")
        if not nb or await nb.get_attribute("aria-disabled") == "true":
            break
        # Robust click: scroll into view, normal click with shorter timeout,
        # fall back to JS-dispatched click if the button is overlapped by a
        # banner/modal/ad. Without this, ~20% of runs fail at random pages.
        clicked = False
        try:
            await nb.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass
        try:
            await nb.click(timeout=10000)
            clicked = True
        except Exception:
            try:
                await pg.evaluate("(el) => el.click()", nb)
                clicked = True
            except Exception:
                pass
        if not clicked:
            print(f"  WARN: could not click 'next page' on page {pnum}; stopping pagination")
            break
        pnum += 1
        await pg.wait_for_timeout(3000)
    print(f"[{cfg.key}] Total:", len(listings), "listings (raw)")

    # Detect bot-throttled partial scrapes. Yad2 sometimes serves a page
    # where the "next" button is missing/disabled even though more results
    # exist — the loop above breaks cleanly and we'd save garbage. Raise
    # so run_leg_with_retry retries with backoff instead of corrupting state.
    if len(listings) < cfg.min_listings_for_trust:
        await context.close()
        raise RuntimeError(
            f"[{cfg.key}] Pagination stopped at page {pnum} with {len(listings)} listings "
            f"(expected >= {cfg.min_listings_for_trust}); likely bot-block. "
            f"Refusing to save partial snapshot."
        )

    # ── Dedupe by listing ID (Yad2 boosts paid ads to multiple search-result pages
    #    under different ?pagination/spot/location query strings — same property,
    #    counted N times). Key on the path segment, ignore query string.
    seen = set()
    deduped = []
    for r in listings:
        lid = extract_id_from_url(r.get("url", ""))
        if not lid or lid in seen:
            continue
        seen.add(lid)
        deduped.append(r)
    if len(deduped) != len(listings):
        print(f"Deduplicated: {len(listings)} -> {len(deduped)} ({len(listings) - len(deduped)} booster duplicates removed)")
    listings = deduped

    # Backfill missing neighborhoods using a street→neighborhood lookup built
    # from listings whose card text DID include a neighborhood.
    enriched, ambiguous = enrich_missing_neighborhoods(listings)
    if enriched:
        print(f"Neighborhood enrichment (street lookup): filled {enriched} listings"
              + (f" ({len(ambiguous)} ambiguous streets skipped)" if ambiguous else ""))

    # ── Canonical neighborhood enrichment via per-neighborhood URLs ────────
    # yad2 has a `&neighborhood=<id>` filter that is the SOURCE OF TRUTH for
    # which neighborhood a listing belongs to (it's set from yad2's internal
    # database, not from the listing's card text). For each known
    # neighborhood we navigate the filtered URL and harvest listing-IDs,
    # then override our card-text inference. IDs map lives in
    # yad2_neighborhood_ids.json; populate it via _discover_neighborhood_ids.py.
    nb_ids_file = os.path.join(OUT, "yad2_neighborhood_ids.json")
    canonical_nb_map = {}
    if os.path.exists(nb_ids_file):
        try:
            with open(nb_ids_file, encoding="utf-8") as f:
                nb_ids = json.load(f)
        except Exception:
            nb_ids = {}
        if nb_ids:
            print(f"Canonical neighborhood scrape: querying {len(nb_ids)} neighborhoods...")
            for nb_name, nb_id in nb_ids.items():
                nb_url = f"https://www.yad2.co.il/realestate/{cfg.feed_path}?city={CITY_ID}&{ROOMS_QS}&neighborhood={nb_id}"
                nb_listing_ids = await collect_listing_ids_from_url(pg, nb_url)
                for lid in nb_listing_ids:
                    canonical_nb_map[lid] = nb_name
                print(f"    {nb_name}: {len(nb_listing_ids)} listings")
            # Apply canonical map: override the 2nd info-part with the
            # authoritative neighborhood from yad2.
            rewritten = 0
            for r in listings:
                lid = extract_id_from_url(r.get("url", ""))
                canonical = canonical_nb_map.get(lid)
                if not canonical:
                    continue
                parts = str(r.get("info", "")).split(",")
                apt_type = parts[0].strip() if parts else "דירה"
                city     = parts[-1].strip() if len(parts) >= 2 else "רעננה"
                new_info = f"{apt_type}, {canonical}, {city}"
                if r.get("info") != new_info:
                    r["info"] = new_info
                    rewritten += 1
            print(f"Canonical mapping rewrote {rewritten} listings; "
                  f"{len(canonical_nb_map)} listing-IDs covered by canonical scrape.")

    # ── Merge fiber-intercepted dates with persistent cache ───────────────
    try:
        with open(cfg.date_posted_file, encoding="utf-8") as f:
            date_cache = json.load(f)
    except:
        date_cache = {}

    # IDs whose cached date is NOT a real Yad2 "published" date but the
    # first_seen guess from the final fallback below. They used to be cached
    # like real dates and never re-fetched, so a one-off fetch failure froze a
    # wrong date for the listing's lifetime — verified on 2026-10-23 against
    # Yad2: a listing published 2025-08-12 stored as 2026-09-17, understating its
    # days-on-market by 13 months (3 of 45 sampled listings were wrong). Guessed
    # dates now stay in this set and are re-fetched every run until a real one
    # is found. Seeded on first use with every cached date equal to first_seen,
    # since that is exactly what the old fallback wrote.
    try:
        with open(cfg.date_unverified_file, encoding="utf-8") as f:
            unverified = set(json.load(f))
    except Exception:
        unverified = {lid for lid, d in date_cache.items() if d and first_seen.get(lid) == d}

    print(f"  React fiber dates found: {len(intercepted_dates)}")

    # Apply fiber dates to listings (date_cache is keyed by listing-ID)
    for r in listings:
        lid = extract_id_from_url(r.get("url", ""))
        date = intercepted_dates.get(lid) or ("" if lid in unverified else date_cache.get(lid, ""))
        if date and intercepted_dates.get(lid):
            unverified.discard(lid)
        r["date_posted"] = date
        if date and lid:
            date_cache[lid] = date

    # ── Fallback: in-browser fetch (uses session cookies, bypasses bot block) ─
    still_missing = [r for r in listings if not r.get("date_posted") and r.get("url")]
    if still_missing:
        print(f"  Fetching {len(still_missing)} dates via in-browser fetch...")
        fetched_ok = 0
        batch_size = 20
        for batch_start in range(0, len(still_missing), batch_size):
            batch = still_missing[batch_start:batch_start + batch_size]
            urls_clean = [r["url"].split("?")[0] for r in batch]
            try:
                results = await pg.evaluate(
                    r"""async (urls) => {
                        return Promise.all(urls.map(async (url) => {
                            try {
                                const resp = await fetch(url);
                                const text = await resp.text();
                                const m = text.match(/פורסם ב[^0-9]*(\d{1,2}\/\d{1,2}\/\d{2,4})/);
                                return m ? m[1] : '';
                            } catch(e) { return ''; }
                        }));
                    }""",
                    urls_clean
                )
            except Exception:
                results = [""] * len(batch)
            for r, raw in zip(batch, results):
                d = parse_yad2_date(raw or "")
                if d:
                    r["date_posted"] = d
                    lid = extract_id_from_url(r.get("url", ""))
                    if lid:
                        date_cache[lid] = d
                        unverified.discard(lid)
                    fetched_ok += 1
            if batch_start + batch_size < len(still_missing):
                print(f"  ...{min(batch_start+batch_size, len(still_missing))}/{len(still_missing)} done")
        print(f"  Got {fetched_ok}/{len(still_missing)} dates via browser fetch")

    # ── Final fallback: use first_seen date when all else fails ─────────
    # both first_seen and date_cache are keyed by listing-ID (stable across runs)
    for r in listings:
        if not r.get("date_posted"):
            lid = extract_id_from_url(r.get("url", ""))
            if not lid:
                continue
            fs_date = first_seen.get(lid, "")
            if fs_date:
                r["date_posted"] = fs_date
                date_cache[lid] = fs_date
            else:
                r["date_posted"] = today
                first_seen[lid] = today
                date_cache[lid] = today
            unverified.add(lid)

    matched = sum(1 for r in listings if r.get("date_posted"))
    print(f"[{cfg.key}]   Total dates resolved: {matched}/{len(listings)} listings")
    with open(cfg.date_posted_file, "w", encoding="utf-8") as f:
        json.dump(date_cache, f, ensure_ascii=False)
    # Only IDs still live matter; removed listings can't be re-fetched anyway.
    live_ids = {extract_id_from_url(r.get("url", "")) for r in listings}
    unverified &= live_ids
    print(f"[{cfg.key}]   Unverified (guessed) dates: {len(unverified)}")
    with open(cfg.date_unverified_file, "w", encoding="utf-8") as f:
        json.dump(sorted(unverified), f)

    await context.close()
    return listings, pnum


def finalize_leg(cfg, listings, pnum, first_seen, today, now):
    """Diff `listings` against cfg's previous-run baseline, compute stats,
    write all of cfg's history/log files, and atomically save the new
    snapshot. Mutates `first_seen` in place (caller owns persisting it
    beyond this call — though this function also writes it to
    cfg.first_seen_file itself, matching the original run()'s behavior)."""
    if not listings:
        print(f"[{cfg.key}] No listings scraped (bot block?). Exiting without overwriting data.")
        return

    # Cross-run maps are keyed by listing-ID (stable across runs). yad2 randomizes
    # the URL query string on every page load, so URL-keyed comparison would mark
    # ~all listings as both "new" and "removed" every run.
    curr_map = {extract_id_from_url(r["url"]): r for r in listings if r.get("url")}

    # ── Load previous run ────────────────────────────────────────────────────
    prev_map = {}
    if os.path.exists(cfg.prev_file):
        try:
            with open(cfg.prev_file, encoding="utf-8") as f:
                prev_map = {extract_id_from_url(r["url"]): r for r in json.load(f) if r.get("url")}
        except Exception:
            prev_map = {}

    # Grace-period state: {listing_id: {"misses": n, "record": {...}, "first_seen": date}}
    pending_removals = {}
    if os.path.exists(cfg.pending_removals_file):
        try:
            with open(cfg.pending_removals_file, encoding="utf-8") as f:
                pending_removals = json.load(f)
        except Exception:
            pending_removals = {}

    # Second-line defense: even if pagination didn't trip the early-stop guard,
    # a sudden drop vs the previous run often means we missed listings (silent
    # partial scrape). Refuse to overwrite the baseline so tomorrow's diff
    # doesn't cascade more false-removals.
    #
    # The threshold is per-leg (see cfg.min_listings_fraction) and relaxes once
    # the baseline is stale: comparing today against a week-old snapshot cannot
    # distinguish a partial scrape from a week of real turnover, and rejecting
    # the run would leave that same stale baseline in place for the next one to
    # be judged against — the ratchet that froze rent for two weeks.
    fraction = cfg.min_listings_fraction
    baseline_note = ""
    try:
        baseline_age_h = (time.time() - os.path.getmtime(cfg.prev_file)) / 3600
    except OSError:
        baseline_age_h = None
    if baseline_age_h is not None and baseline_age_h > STALE_BASELINE_HOURS:
        fraction = min(fraction, STALE_BASELINE_FRACTION)
        baseline_note = (f" [baseline is {baseline_age_h:.0f}h old — threshold "
                         f"relaxed to {int(fraction*100)}%]")
        print(f"[{cfg.key}] Baseline {baseline_age_h:.0f}h old; partial-scrape "
              f"threshold relaxed to {int(fraction*100)}%.")
    if prev_map and len(curr_map) < fraction * len(prev_map):
        raise RuntimeError(
            f"[{cfg.key}] Listing count dropped from {len(prev_map)} to {len(curr_map)} "
            f"({len(curr_map)/len(prev_map)*100:.1f}% of previous, "
            f"threshold {int(fraction*100)}%); "
            f"likely partial scrape. Refusing to save.{baseline_note}"
        )

    curr_ids = set(curr_map)
    prev_ids = set(prev_map)

    # ── Grace-period removal detection ─────────────────────────────────────────
    # A listing missing from a single run's feed is often still live (Yad2's feed
    # flaps). Count consecutive misses; only confirm a removal after
    # REMOVAL_GRACE_RUNS absences. Each pending entry carries the listing's
    # last-known record + first_seen so it can still be logged once confirmed,
    # after prev_run no longer contains it. A reappearance clears the pending
    # state (and is not counted as a brand-new listing).
    absent_now = (prev_ids | set(pending_removals)) - curr_ids
    reappeared = set(pending_removals) & curr_ids

    confirmed_removed = {}   # lid -> {"record": {...}, "first_seen": date}
    still_pending     = {}
    now_ts = time.time()
    for lid in absent_now:
        entry  = pending_removals.get(lid) or {}
        misses = entry.get("misses", 0) + 1
        record = entry.get("record") or prev_map.get(lid)
        if record is None:
            continue
        fs = entry.get("first_seen") or first_seen.get(lid, today)
        # Wall-clock clock starts at the FIRST miss and survives across runs, so
        # a burst of closely-spaced runs can't race a listing to "removed".
        first_missed = entry.get("first_missed_at") or now_ts
        elapsed_h = (now_ts - first_missed) / 3600
        if misses >= REMOVAL_GRACE_RUNS and elapsed_h >= REMOVAL_GRACE_HOURS:
            confirmed_removed[lid] = {"record": record, "first_seen": fs}
        else:
            still_pending[lid] = {"misses": misses, "record": record,
                                  "first_seen": fs, "first_missed_at": first_missed}
    pending_removals = still_pending

    removed_ids = set(confirmed_removed)
    new_ids     = curr_ids - prev_ids - reappeared
    common_ids  = curr_ids & prev_ids
    if reappeared:
        print(f"Grace period: {len(reappeared)} listing(s) reappeared (cancelled pending removal); "
              f"{len(still_pending)} now pending, {len(confirmed_removed)} confirmed removed")

    # ── Add new IDs to first_seen ─────────────────────────────────────────────
    for lid in new_ids:
        if lid and lid not in first_seen:
            first_seen[lid] = today

    # Self-heal: every live listing must have a first_seen. Only NEW ids were
    # ever added, so a listing that was already in the baseline but missing from
    # first_seen (54 such on 2026-10-23, all first archived on 2026-09-23 /
    # 2026-10-06 — overlapping runs from before the single-instance lock, each
    # saving its own stale copy of first_seen) was never added, and its eventual
    # removal was logged with DOM 0. Backfill from the earliest snapshot in the
    # append-only archive, which is when we really first saw it.
    missing_fs = [lid for lid in curr_ids if lid and lid not in first_seen]
    if missing_fs:
        earliest = _archive_first_seen(cfg.archive_file, set(missing_fs))
        for lid in missing_fs:
            first_seen[lid] = earliest.get(lid, today)
        print(f"[{cfg.key}] Backfilled first_seen for {len(missing_fs)} listing(s) "
              f"({len(earliest)} from the archive)")

    # ── DOM log for confirmed removed listings ────────────────────────────────
    dom_days_list = []
    dom_rows = []
    for lid, info in confirmed_removed.items():
        r  = info["record"]
        fs = info["first_seen"]
        try:
            dom = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(fs, "%Y-%m-%d")).days
        except:
            dom = 0
        dom_days_list.append(dom)
        nb  = extract_neighborhood(r.get("info",""))
        apt = str(r.get("info","")).split(",")[0].strip() if r.get("info") else ""
        dom_rows.append({
            "removed_date": today,
            "url": r.get("url", ""),
            "first_seen": fs,
            "dom_days": dom,
            "price": r.get("price",""),
            "neighborhood": nb,
            "size_sqm": r.get("size_sqm",""),
            "apt_type": apt,
        })
    if dom_rows:
        dom_exists = os.path.exists(cfg.dom_log_file)
        with open(cfg.dom_log_file, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["removed_date","url","first_seen","dom_days","price","neighborhood","size_sqm","apt_type"])
            if not dom_exists: w.writeheader()
            w.writerows(dom_rows)

    # ── Price changes ─────────────────────────────────────────────────────────
    cuts = rises = 0
    cut_pcts = []
    for lid in common_ids:
        pp = parse_price_num(prev_map[lid].get("price",""))
        cp = parse_price_num(curr_map[lid].get("price",""))
        if pp and cp:
            if cp < pp:
                cuts += 1
                cut_pcts.append((pp - cp) / pp * 100)
            elif cp > pp:
                rises += 1

    # ── Survival rate (30 days) ───────────────────────────────────────────────
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    old_ids = {i for i, d in first_seen.items() if d <= cutoff}
    still_alive = old_ids & set(curr_map)
    survival_30d = round(len(still_alive) / len(old_ids) * 100, 1) if old_ids else None

    # ── Summary stats ─────────────────────────────────────────────────────────
    # Stats and history aggregations use only sane listings — Yad2 data-entry
    # typos (a ₪12,700 apartment, 10 m² or 11,526 m² sizes) would poison
    # averages, min/max and price-per-m². The snapshot, diff and save below
    # still keep every listing; this only cleans the derived statistics
    # (mirrors the dashboard's display filter so both agree).
    def _stats_sane(r):
        p = parse_price_num(r.get("price", ""))
        try: s = float(r.get("size_sqm") or 0)
        except Exception: s = 0
        if p is not None and p < cfg.min_sane_price: return False
        if s and (s < 25 or s > 1000): return False
        # ₪/m² band — only applied when BOTH figures are present, so a listing
        # missing either one is still kept (matching the policy above).
        if p is not None and s:
            ppsqm = p / s
            if ppsqm < cfg.min_sane_ppsqm or ppsqm > cfg.max_sane_ppsqm:
                return False
        return True
    stats_listings = [r for r in listings if _stats_sane(r)]

    prices = [parse_price_num(r["price"]) for r in stats_listings]
    prices = [p for p in prices if p]
    sizes  = []
    for r in stats_listings:
        try:
            s = float(r["size_sqm"] or 0)
            p = parse_price_num(r["price"])
            if s and p: sizes.append(p / s)
        except: pass

    sp = sorted(prices)
    n  = len(sp)
    avg_price    = round(sum(prices) / n)        if n else 0
    median_price = sp[n // 2]                    if n else 0
    min_price    = sp[0]                         if n else 0
    max_price    = sp[-1]                        if n else 0
    avg_ppsqm    = round(sum(sizes) / len(sizes)) if sizes else 0
    avg_cut_pct  = round(sum(cut_pcts) / len(cut_pcts), 2) if cut_pcts else 0
    absorption   = round(len(removed_ids) / len(prev_map) * 100, 2) if prev_map else 0
    avg_dom      = round(sum(dom_days_list) / len(dom_days_list), 1) if dom_days_list else None

    # avg DOM of currently active listings (today - date_posted, falling back to first_seen)
    active_doms = []
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    for r in stats_listings:
        d = r.get("date_posted") or first_seen.get(extract_id_from_url(r.get("url", "")), "")
        if not d:
            continue
        try:
            days = (today_dt - datetime.strptime(d[:10], "%Y-%m-%d")).days
            if days >= 0:
                active_doms.append(days)
        except Exception:
            pass
    avg_active_dom = round(sum(active_doms) / len(active_doms), 1) if active_doms else None

    # ── Append to history CSV ─────────────────────────────────────────────────
    hist_exists = os.path.exists(cfg.history_file)
    with open(cfg.history_file, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not hist_exists:
            w.writerow(["timestamp","count","avg_price","median_price","min_price","max_price",
                        "avg_price_per_sqm","price_cuts","price_rises",
                        "avg_cut_pct","absorption_rate","survival_30d","avg_dom","avg_active_dom"])
        w.writerow([now, len(stats_listings), avg_price, median_price, min_price, max_price,
                    avg_ppsqm, cuts, rises, avg_cut_pct, absorption,
                    survival_30d if survival_30d is not None else "",
                    avg_dom if avg_dom is not None else "",
                    avg_active_dom if avg_active_dom is not None else ""])

    # ── Per-listing active DOM (today − date_posted) for the breakdowns below ──
    nb_active_doms    = defaultdict(list)
    type_active_doms  = defaultdict(list)
    rooms_active_doms = defaultdict(list)
    for r in stats_listings:
        d = r.get("date_posted") or first_seen.get(extract_id_from_url(r.get("url","")), "")
        if not d:
            continue
        try:
            days = (today_dt - datetime.strptime(d[:10], "%Y-%m-%d")).days
            if days < 0:
                continue
        except Exception:
            continue
        nb  = extract_neighborhood(r.get("info",""))
        apt = str(r.get("info","")).split(",")[0].strip() or "דירה"
        rb  = rooms_bucket(r.get("rooms"))
        if not rb:
            continue
        if nb:
            nb_active_doms[(nb, rb)].append(days)
        type_active_doms[(apt, rb)].append(days)
        rooms_active_doms[rb].append(days)

    # ── Neighborhood history (split by room bucket) ────────────────────────────
    # Keyed by (neighborhood, rooms) so the dashboard's 4/5 toggle can show a
    # neighborhood's own 4-room OR 5-room trend instead of a mixed line.
    nb_prices = defaultdict(list)
    nb_ppsqm  = defaultdict(list)
    for r in stats_listings:
        nb = extract_neighborhood(r.get("info",""))
        rb = rooms_bucket(r.get("rooms"))
        if not nb or not rb: continue
        p = parse_price_num(r.get("price",""))
        try: s = float(r.get("size_sqm") or 0)
        except: s = 0
        if p: nb_prices[(nb, rb)].append(p)
        if p and s: nb_ppsqm[(nb, rb)].append(p / s)

    nb_cols = ["timestamp","neighborhood","rooms","avg_price","avg_price_per_sqm","count","avg_active_dom"]
    ensure_csv_columns(cfg.nb_history_file, nb_cols)
    nb_exists = os.path.exists(cfg.nb_history_file)
    with open(cfg.nb_history_file, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not nb_exists:
            w.writerow(nb_cols)
        for (nb, rb) in nb_prices:
            ppsqm_avg = round(sum(nb_ppsqm[(nb, rb)]) / len(nb_ppsqm[(nb, rb)])) if nb_ppsqm.get((nb, rb)) else 0
            doms = nb_active_doms.get((nb, rb), [])
            nb_dom = round(sum(doms) / len(doms), 1) if doms else ""
            w.writerow([now, nb, rb, round(sum(nb_prices[(nb, rb)]) / len(nb_prices[(nb, rb)])), ppsqm_avg, len(nb_prices[(nb, rb)]), nb_dom])

    # ── Type history (split by room bucket) ──────────────────────────────────────
    type_prices = defaultdict(list)
    type_ppsqm  = defaultdict(list)
    for r in stats_listings:
        apt = str(r.get("info","")).split(",")[0].strip() or "דירה"
        rb  = rooms_bucket(r.get("rooms"))
        if not rb: continue
        p = parse_price_num(r.get("price",""))
        try: s = float(r.get("size_sqm") or 0)
        except: s = 0
        if p: type_prices[(apt, rb)].append(p)
        if p and s: type_ppsqm[(apt, rb)].append(p / s)

    type_cols = ["timestamp","apt_type","rooms","avg_price","avg_price_per_sqm","count","avg_active_dom"]
    ensure_csv_columns(cfg.type_history_file, type_cols)
    type_exists = os.path.exists(cfg.type_history_file)
    with open(cfg.type_history_file, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not type_exists:
            w.writerow(type_cols)
        for (apt, rb) in type_prices:
            ppsqm_avg = round(sum(type_ppsqm[(apt, rb)]) / len(type_ppsqm[(apt, rb)])) if type_ppsqm.get((apt, rb)) else 0
            doms = type_active_doms.get((apt, rb), [])
            t_dom = round(sum(doms) / len(doms), 1) if doms else ""
            w.writerow([now, apt, rb, round(sum(type_prices[(apt, rb)]) / len(type_prices[(apt, rb)])), ppsqm_avg, len(type_prices[(apt, rb)]), t_dom])

    # ── Rooms history (bucketed 4 vs 5) ──────────────────────────────────────────
    rooms_prices = defaultdict(list)
    rooms_ppsqm  = defaultdict(list)
    # Bucket membership is counted separately from the price list. Prices are
    # only collected for listings with a parseable price, but a listing with no
    # price ("price on request") is still a real listing in that room bucket.
    # Using len(prices) as the count made the room buckets sum to LESS than
    # yad2_history's count (which is len(stats_listings)) — a ~9-listing gap
    # that made the two files silently disagree about market size.
    rooms_count  = Counter()
    for r in stats_listings:
        rb = rooms_bucket(r.get("rooms"))
        if not rb: continue
        rooms_count[rb] += 1
        p = parse_price_num(r.get("price",""))
        try: s = float(r.get("size_sqm") or 0)
        except: s = 0
        if p: rooms_prices[rb].append(p)
        if p and s: rooms_ppsqm[rb].append(p / s)

    rooms_cols = ["timestamp","rooms","avg_price","median_price","avg_price_per_sqm","count","avg_active_dom"]
    ensure_csv_columns(cfg.rooms_history_file, rooms_cols)
    rooms_exists = os.path.exists(cfg.rooms_history_file)
    with open(cfg.rooms_history_file, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not rooms_exists:
            w.writerow(rooms_cols)
        for rb in sorted(rooms_count):
            ps = sorted(rooms_prices[rb])
            ppsqm_avg = round(sum(rooms_ppsqm[rb]) / len(rooms_ppsqm[rb])) if rooms_ppsqm.get(rb) else 0
            doms = rooms_active_doms.get(rb, [])
            r_dom = round(sum(doms) / len(doms), 1) if doms else ""
            avg_p = round(sum(ps) / len(ps)) if ps else 0
            med_p = ps[len(ps)//2] if ps else 0
            w.writerow([now, rb, avg_p, med_p, ppsqm_avg, rooms_count[rb], r_dom])

    # ── Save files (write to temp then rename so a crash never zeros the file) ──
    import tempfile
    with tempfile.NamedTemporaryFile("w", dir=OUT, suffix=".json", delete=False, encoding="utf-8") as tf:
        json.dump(listings, tf, ensure_ascii=False, indent=2)
        tmp_json = tf.name
    os.replace(tmp_json, cfg.json_file)
    with tempfile.NamedTemporaryFile("w", dir=OUT, suffix=".csv", delete=False,
                                     newline="", encoding="utf-8-sig") as tf:
        w = csv.DictWriter(tf, fieldnames=listings[0].keys())
        w.writeheader(); w.writerows(listings)
        tmp_csv = tf.name
    os.replace(tmp_csv, cfg.csv_file)

    # ── Append every listing to the permanent, append-only archive ──────────────
    # cfg.json_file/csv_file are overwritten each run — a bad run (or a bug) can
    # only ever lose what's IN that one snapshot. This file is never rewritten,
    # only appended to, so every listing ever seen stays recoverable here even
    # if something upstream corrupts or empties the live snapshot.
    archive_cols = ["snapshot_time"] + list(listings[0].keys())
    archive_exists = os.path.exists(cfg.archive_file)
    with open(cfg.archive_file, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not archive_exists:
            w.writerow(archive_cols)
        for r in listings:
            w.writerow([now] + [r.get(k, "") for k in listings[0].keys()])

    # Preserve the previous run's snapshot (copy2 keeps its original mtime, which
    # the dashboard shows as the "since" time) BEFORE overwriting PREV_FILE with
    # this run. Best-effort — never let it fail the scrape.
    try:
        if os.path.exists(cfg.prev_file):
            import shutil
            shutil.copy2(cfg.prev_file, cfg.display_prev_file)
    except Exception as e:
        print(f"[{cfg.key}]   WARN: could not update display baseline: {e}")
    with open(cfg.prev_file, "w", encoding="utf-8") as f:
        json.dump(listings, f, ensure_ascii=False, indent=2)
    with open(cfg.first_seen_file, "w", encoding="utf-8") as f:
        json.dump(first_seen, f, ensure_ascii=False, indent=2)
    with open(cfg.pending_removals_file, "w", encoding="utf-8") as f:
        json.dump(pending_removals, f, ensure_ascii=False, indent=2)

    print(f"[{cfg.key}] Saved: {len(listings)} listings")
    print(f"[{cfg.key}] New: {len(new_ids)} | Removed: {len(removed_ids)} | Price cuts: {cuts} (avg {avg_cut_pct}%)")
    print(f"[{cfg.key}] Absorption: {absorption}% | Survival 30d: {survival_30d}%")
    if dom_days_list:
        print(f"[{cfg.key}] Avg DOM (removed this run): {avg_dom} days")

    # ── Run log ───────────────────────────────────────────────────────────────
    log_exists = os.path.exists(cfg.run_log_file)
    with open(cfg.run_log_file, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not log_exists:
            w.writerow(["timestamp","status","pages_scraped","total_listings",
                        "new_listings","removed_listings","price_cuts","price_rises",
                        "avg_cut_pct","avg_price","median_price","min_price","max_price",
                        "avg_price_per_sqm","absorption_rate","survival_30d","avg_dom","error"])
        w.writerow([now, "success", pnum - 1, len(listings),
                    len(new_ids), len(removed_ids), cuts, rises,
                    avg_cut_pct, avg_price, median_price, min_price, max_price,
                    avg_ppsqm, absorption,
                    survival_30d if survival_30d is not None else "",
                    avg_dom if avg_dom is not None else "", ""])
    print(f"[{cfg.key}] Run log updated: {cfg.run_log_file}")

def log_error(run_log_file, error_msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_exists = os.path.exists(run_log_file)
    with open(run_log_file, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not log_exists:
            w.writerow(["timestamp","status","pages_scraped","total_listings",
                        "new_listings","removed_listings","price_cuts","price_rises",
                        "avg_cut_pct","avg_price","median_price","min_price","max_price",
                        "avg_price_per_sqm","absorption_rate","survival_30d","avg_dom","error"])
        w.writerow([now, "error", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", error_msg])

async def run_leg_with_retry(p, cfg, first_seen, max_attempts=2,
                              retry_delays_s=(300, 600, 1200, 2400, 3600)):
    """Run one leg (scrape + finalize) with retry-and-backoff for transient
    failures (click timeouts, network blips, bot blocks) — scoped to a
    single deal type so a bot-block on one leg never re-scrapes the other,
    already-saved leg. Only the FINAL outcome lands in cfg.run_log_file —
    intermediate retries are printed but not logged, so the operator sees
    one row per invocation regardless of how many retries it took.

    Re-warms Radware clearance before each retry (not before the first
    attempt — the caller already warmed once, shared across both legs),
    mirroring the original run_with_retry()'s behavior where every retry of
    run() re-warmed as its first line.

    Default budget: 2 attempts, 5min apart — one retry after the first
    failure, then give up. Never raises — owns logging its own leg's
    outcome."""
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            today = shift_saturday_to_friday(datetime.now().strftime("%Y-%m-%d"))
            now   = datetime.now().strftime("%Y-%m-%d %H:%M")
            listings, pnum = await run_leg(p, cfg, first_seen, today)
            finalize_leg(cfg, listings, pnum, first_seen, today, now)
            return
        except Exception as e:
            last_err = e
            print(f"[{cfg.key}] Attempt {attempt}/{max_attempts} failed: {e}")
            if attempt < max_attempts:
                delay = retry_delays_s[min(attempt - 1, len(retry_delays_s) - 1)]
                print(f"  [{cfg.key}] retrying in {delay}s ({delay // 60} min)...")
                await asyncio.sleep(delay)
                # The re-warm must not escape this handler. It used to be awaited
                # bare, so a failed warm raised straight out of the "never raises"
                # contract into run_all()'s top-level handler, which logs to BOTH
                # legs' run logs — overwriting this leg's REAL error with a
                # generic Radware message. That is why a rent leg failing the
                # partial-scrape guard was reported for two weeks as a bot-block.
                try:
                    await ensure_radware_clearance(p, url=cfg.url)
                except Exception as warm_err:
                    print(f"  [{cfg.key}] re-warm failed ({warm_err}); "
                          f"continuing to next attempt anyway.")
    print(f"[{cfg.key}] ERROR (after retries): {last_err}")
    log_error(cfg.run_log_file, str(last_err))


def _archive_first_seen(archive_file, ids):
    """Earliest archive snapshot date (YYYY-MM-DD, Saturday->Friday) per listing
    ID, for the requested IDs only."""
    out = {}
    try:
        with open(archive_file, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                lid = extract_id_from_url(row.get("url", ""))
                if lid in ids:
                    d = shift_saturday_to_friday(str(row.get("snapshot_time", ""))[:10])
                    if d and (lid not in out or d < out[lid]):
                        out[lid] = d
    except OSError:
        pass
    return out


def _load_json_or_default(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


async def ensure_radware_clearance_with_retry(p, url, max_attempts=2,
                                               retry_delays_s=(300, 600, 1200, 2400, 3600)):
    """Wrap ensure_radware_clearance with the same retry-and-backoff budget as
    run_leg_with_retry (2 attempts, 5min apart). Previously a single failed
    warm-up (e.g. the browser itself crashing on launch) aborted the entire
    invocation with no retry at all — see the 08/08 run_log entries. Now
    allows exactly one retry instead of retrying repeatedly. Re-raises after
    exhausting every attempt so run_all()'s top-level handler still logs a
    final failure instead of retrying forever."""
    for attempt in range(1, max_attempts + 1):
        try:
            await ensure_radware_clearance(p, url)
            return
        except Exception as e:
            print(f"[warmup] Attempt {attempt}/{max_attempts} failed: {e}")
            if attempt == max_attempts:
                raise
            delay = retry_delays_s[min(attempt - 1, len(retry_delays_s) - 1)]
            print(f"  [warmup] retrying in {delay}s ({delay // 60} min)...")
            await asyncio.sleep(delay)


async def run_all():
    """Combined entry point: scrape sale, then rent, in one invocation,
    sharing a single Radware warm-up (clearance is domain-level, not
    path-specific, so warming once on the sale URL also clears rent)."""
    first_seen = {cfg.key: _load_json_or_default(cfg.first_seen_file, {}) for cfg in DEAL_CONFIGS}
    async with async_playwright() as p:
        await ensure_radware_clearance_with_retry(p, url=SALE_CFG.url)
        for cfg in DEAL_CONFIGS:
            await run_leg_with_retry(p, cfg, first_seen[cfg.key])


if not acquire_single_instance_lock():
    print("Another scraper instance is already running; exiting.")
    sys.exit(0)
try:
    asyncio.run(run_all())
except Exception as e:
    # Only reachable for a catastrophic failure before either leg's own
    # per-leg logging ran (e.g. Playwright itself failed to launch).
    print(f"ERROR (top-level): {e}")
    log_error(SALE_CFG.run_log_file, str(e))
    log_error(RENT_CFG.run_log_file, str(e))
finally:
    release_single_instance_lock()
