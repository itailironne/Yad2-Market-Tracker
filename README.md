# Yad2 Real Estate Market Tracker — Ra'anana 4-Room Apartments

A fully automated system that scrapes, tracks, and visualises the Ra'anana 4-room apartment market on Yad2. It runs twice daily, detects every new listing, price change, and removal, and presents everything in a live interactive dashboard.

---

## How It Works

```
Yad2 Website
     │
     ▼
yad2_scraper.py  ──────────────────────────────────────────────────────
│  1. Opens Yad2 feed page (18+ pages) via Playwright browser           │
│  2. Extracts all listing cards (price, street, rooms, floor, sqm)     │
│  3. Fetches real posting date for each listing via in-browser fetch   │
│  4. Detects new listings, removed listings, price changes             │
│  5. Computes market stats (avg price, absorption, DOM, survival...)   │
│  6. Saves everything to data files                                    │
└───────────────────────────────────────────────────────────────────────
     │
     ▼  writes to ──►
┌─────────────────────────────────────────────────────────────────────┐
│  DATA FILES                                                          │
│  yad2_raanana_4rooms.json / .csv   — current listings snapshot      │
│  yad2_prev_run.json                — previous run snapshot           │
│  yad2_first_seen.json              — URL → first-seen date           │
│  yad2_date_posted.json             — URL → real Yad2 posting date    │
│  yad2_history.csv                  — market stats time-series        │
│  yad2_neighborhood_history.csv     — neighbourhood price history     │
│  yad2_dom_log.csv                  — removed listings + DOM          │
│  yad2_run_log.csv                  — log of every scraper run        │
└─────────────────────────────────────────────────────────────────────┘
     │
     ▼  reads from ──►
yad2_dashboard.py  (Streamlit)
     │
     ▼
Browser dashboard at http://localhost:8501
```

---

## Running the Scraper

```bash
python yad2_scraper.py
```

- Takes ~5–10 minutes (18 pages + date fetching for all listings)
- Scheduled to run automatically at **08:00** and **20:00** daily
- Output is printed to console: pages scraped, dates fetched, changes detected
- **Opens real Chrome windows** for ~1 minute at the start (the anti-bot warm-up,
  see [Bot Protection](#bot-protection-radware--the-chrome-warm-up) below), then a
  scraping window for the rest of the run. This is expected — leave them alone.
- **Must run in a logged-on desktop session.** The scrape is headful (a visible
  browser), so it cannot run as a background/session-0 task. The scheduled tasks
  are already set to *Interactive* logon, which is correct.
- Only **one** scraper runs at a time — a lock file (`.yad2_scraper.lock`) makes
  overlapping launches (scheduled + watchdog + manual) exit immediately instead
  of fighting over the browser profile.

---

## Opening the Dashboard

**Option A — double-click:**  
`פתח דשבורד יד2.bat`

**Option B — terminal:**
```bash
streamlit run yad2_dashboard.py
```

Opens at `http://localhost:8501`

---

## File Reference

| File | Updated by | Purpose |
|------|-----------|---------|
| `yad2_scraper.py` | (you run it) | Main scraper script |
| `yad2_dashboard.py` | (you edit it) | Streamlit dashboard |
| `פתח דשבורד יד2.bat` | — | Shortcut to launch dashboard |
| `yad2_raanana_4rooms.json` | scraper | Full current listings with all fields |
| `yad2_raanana_4rooms.csv` | scraper | Same data as CSV (for Excel etc.) |
| `yad2_prev_run.json` | scraper | Snapshot of the previous run — diff against this to detect changes |
| `yad2_first_seen.json` | scraper | Dictionary: URL → date we first saw this listing |
| `yad2_date_posted.json` | scraper | Cache: URL → real Yad2 posting date (so pages aren't re-fetched) |
| `yad2_history.csv` | scraper | One row per run: market-wide stats over time |
| `yad2_neighborhood_history.csv` | scraper | One row per neighbourhood per run: price trends |
| `yad2_dom_log.csv` | scraper | Every removed listing with its days-on-market |
| `yad2_run_log.csv` | scraper | Every run: status, counts, errors |

---

## Listing Data Fields

Each record in `yad2_raanana_4rooms.json` (and `.csv`) has:

| Field | Example | Description |
|-------|---------|-------------|
| `price` | `₪ 2,900,000` | Asking price as shown on Yad2 |
| `street` | `הגלבוע` | Street name |
| `info` | `דירה, לב הפארק, רעננה` | Apt type, neighbourhood, city |
| `rooms` | `4` | Number of rooms |
| `floor` | `3` | Floor number |
| `size_sqm` | `100` | Size in square metres |
| `url` | `https://www.yad2.co.il/...` | Direct link to listing |
| `date_posted` | `2025-07-10` | Real date the seller posted on Yad2 |

The dashboard also computes two derived columns at display time:

| Column | How computed |
|--------|-------------|
| `תאריך הופעה` (appearance date) | `date_posted` if available, else `first_seen` date |
| `ימים בשוק` (days on market) | `today − date_posted` |

---

## History & Statistics Files

### `yad2_history.csv`
One row per scraper run with market-wide stats:

| Column | Description |
|--------|-------------|
| `timestamp` | Date and time of run |
| `count` | Total active listings |
| `avg_price` | Average asking price |
| `median_price` | Median asking price |
| `min_price` | Cheapest listing |
| `max_price` | Most expensive listing |
| `avg_price_per_sqm` | Average price per m² |
| `price_cuts` | Number of listings that lowered price |
| `price_rises` | Number of listings that raised price |
| `avg_cut_pct` | Average % of price cuts |
| `absorption_rate` | % of listings removed this run (sold/withdrawn) |
| `survival_30d` | % of listings that were still active after 30 days |
| `avg_dom` | Average days-on-market for listings removed this run |

### `yad2_neighborhood_history.csv`
One row per neighbourhood per run:

| Column | Description |
|--------|-------------|
| `timestamp` | Date and time of run |
| `neighborhood` | Neighbourhood name |
| `avg_price` | Average price in that neighbourhood |
| `avg_price_per_sqm` | Average price per m² |
| `count` | Number of active listings |

### `yad2_dom_log.csv`
One row per listing that was removed (sold or taken down):

| Column | Description |
|--------|-------------|
| `removed_date` | Date we noticed it was gone |
| `url` | Listing URL |
| `first_seen` | Date we first saw this listing |
| `dom_days` | Days on market (removed_date − first_seen) |
| `price` | Last known price |
| `neighborhood` | Neighbourhood |
| `size_sqm` | Size |
| `apt_type` | Apartment type |

### `yad2_run_log.csv`
One row per scraper run:

| Column | Description |
|--------|-------------|
| `timestamp` | When the run started |
| `status` | `success` or `error` |
| `pages_scraped` | Number of feed pages scraped |
| `total_listings` | Total listings found |
| `new_listings` | New listings since last run |
| `removed_listings` | Listings gone since last run |
| `price_cuts` / `price_rises` | Price movements |
| `avg_cut_pct` | Average price cut % |
| `avg_price` / `median_price` / etc. | Market stats for that run |
| `absorption_rate` | % removed this run |
| `survival_30d` | 30-day survival rate |
| `avg_dom` | Average DOM of removed listings |
| `error` | Error message if status = error |

---

## Dashboard Sections

| Section | What it shows |
|---------|--------------|
| **Sidebar** | Filters: price range, size, apt type, rooms, floor, neighbourhood. Live status panel showing the last update time, listing count, and pills with new/removed/price-changes since the previous run. |
| **Page header** | Eyebrow badge, gradient title, last-update timestamp. |
| **Run-status banner** | Always-visible health indicator at the top. Green ✅ when the last run succeeded, red ❌ with the exact error message when it failed, yellow ⚠️ when the last run is more than 14 hours old. |
| **KPI strip** | Active listings · Avg price · Median price · Min price · Price per m². Each card has an icon and a gradient value. |
| **Market trends** | Listing quantity over time · Avg price per m² over time · Price cuts vs rises per run · Avg cut depth %. Filterable from the sidebar by neighbourhood and apartment type. |
| **Changes since last run** | 4 delta tiles (new / removed / cuts / rises) plus tabs with full tables: new listings, removed listings, price changes (before → after). |
| **Full table (AgGrid)** | All active listings with Excel-style filter buttons (▼) on every column header. Includes price, street, neighbourhood, type, rooms, floor, size, **date posted**, **days on market**, and a link button. |
| **Run log** | History of every scraper run with all stats. |

### Chart behaviour
- **One point per day**: same-day scraper runs are collapsed via a `_daily()` helper so each calendar day shows only once on the x-axis.
- **No zoom**: charts are read-only — `dragmode=False`, `scrollZoom=False`, and `fixedrange=True` on both axes.
- **Categorical x-axis**: dates render as string labels (`%d/%m/%y`) so they never duplicate.

---

## Saturday → Friday Rule

Yad2 activity drops sharply on Shabbat (Saturday in Israel). To prevent Saturday from skewing the charts:

- **In the scraper** — `shift_saturday_to_friday(date_str)` automatically rewrites any date that lands on a Saturday to the previous Friday. It is applied to:
  - `today` (used for `first_seen` and `removed_date`)
  - every `date_posted` parsed from Yad2 (via `parse_yad2_date`)
- **In history files** — `yad2_history.csv`, `yad2_neighborhood_history.csv`, `yad2_type_history.csv`, and `yad2_run_log.csv` exclude Saturday rows entirely.
- **Existing data** — was retroactively cleaned by `_cleanup_saturdays.py` (one-shot script). A backup of all originals lives in `_backup_before_saturday_cleanup/`.

The result: the dashboard never shows Saturday as a separate day — its activity is rolled into Friday.

---

## Bot Protection (Radware) & the Chrome Warm-Up

Yad2 sits behind **Radware Bot Manager** (its client-side script is `stormcaster`).
A cold automated browser — Playwright driving Chromium over CDP, headless or not —
is served a **"Radware Page"** JavaScript challenge that never clears. When that
happens the feed renders zero listings and pagination dies on page 1, producing
the tell-tale error:

```
Pagination stopped at page 1 (expected >= 10); likely bot-block.
```

A *genuine* Chrome, however, solves the same challenge automatically (no CAPTCHA)
and stores clearance cookies (`uzmx`, `__uzm*`) in its profile. The scraper
exploits this in two phases:

1. **Warm-up** — `warm_clearance()` launches a **real, visible Chrome** (via
   `channel="chrome"`) on a dedicated profile (`.yad2_chrome_profile/`), waits
   ~40s for it to pass the challenge, then closes it. `ensure_radware_clearance()`
   opens a throwaway Playwright context to *confirm* the feed actually renders,
   and re-warms with more time if a given attempt didn't take.
2. **Scrape** — Playwright reopens that same warmed profile with
   `launch_persistent_context(channel="chrome", headless=False)` and inherits the
   clearance, so the whole 18-page scrape (plus per-neighborhood sweeps and the
   in-browser date fetches) sails through.

Why it must be this way — each was verified against the live site:

| Constraint | Reason |
|-----------|--------|
| **Genuine Chrome for the warm-up** | Radware fingerprints Playwright's CDP channel; a cold Playwright browser is blocked even with `navigator.webdriver` masked. |
| **Visible, on-screen window** | The challenge checks page visibility — off-screen or minimized warm-up windows do **not** clear. Hence the run must be in a logged-on session. |
| **Headful scrape** | Headless Chrome is re-fingerprinted and re-challenged even *with* valid clearance cookies. |
| **No spoofed user-agent** | A UA that contradicts the browser's real client-hints is itself a bot signal. (The previous hard-coded `Chrome/124` UA was one reason detection tightened.) |
| **Single-instance lock** | Two runs would fight over the one Chrome profile and clobber each other's output. |

The dedicated profile and the lock file are machine-local and git-ignored.

---

## Date Extraction — How It Works

Getting the real posting date from Yad2 requires multiple attempts in order:

1. **React fiber state** — reads dates directly from React component memory on the feed page (zero extra requests). Works when Yad2 exposes the date in component props.
2. **Network response interception** — captures Yad2's own API JSON responses during page load and extracts dates from them automatically.
3. **In-browser fetch fallback** — for any listing still missing a date, the scraper uses the already-loaded browser (which has valid session cookies and Radware clearance) to fetch each individual listing page via JavaScript `fetch()`. This rides the cleared session past Yad2's bot-protection. Parses `פורסם ב DD/MM/YY` from the HTML. Runs in batches of 20 in parallel.
4. **First-seen safety net** — if all else fails, uses the date we first noticed the listing in our tracker.

Every date that comes out of these steps is then run through `shift_saturday_to_friday()` so Saturdays never enter the dataset.

Fetched dates are permanently cached in `yad2_date_posted.json` so they are never re-fetched on subsequent runs.

---

## Design / UI

- **Theme**: light, slate-based (#f8fafc bg, #ffffff cards, #2563eb→#06b6d4 brand gradient).
- **Typography**: Inter + Heebo (Hebrew), 800-weight gradient title, refined size hierarchy.
- **KPI cards**: white with subtle border, hover lift, top accent bar that slides in on hover, gradient value text.
- **Tabs**: pill-style, selected tab gets a blue→cyan gradient with shadow.
- **AgGrid table**: striped rows, hover state, rounded corners, custom link buttons.
- **Charts**: transparent backgrounds (cards show through), light grid, larger markers with white outlines.
- **Run-status banner**: gradient backgrounds (green/red/yellow) with subtle shadow.

---

## Technical Requirements

```
Python 3.10+
Google Chrome  (the real, installed browser — driven via channel="chrome" and
               used to warm Radware clearance; not Playwright's bundled Chromium)
playwright (pip install playwright)
streamlit
streamlit-aggrid
pandas
plotly
```

---

## Automation Schedule

The scraper is configured to run automatically at **08:00** and **20:00** every day via Windows Task Scheduler. Each run takes ~5–10 minutes.

### Important Task Scheduler settings
For each task (Yad2_Morning / Yad2_Evening), under **Properties**:
- **General tab** → ✅ *Run only when user is logged on* (an **Interactive** logon).
  The scrape is headful — it opens a visible Chrome window — so it needs a real
  desktop session. A "run whether user is logged on or not" task runs in session 0
  with no desktop and the anti-bot warm-up will fail.
- **Settings tab** → ✅ *Run task as soon as possible after a scheduled start is missed*
- **Conditions tab** → ✅ *Wake the computer to run this task*

Without these, if the computer is asleep or logged off at 08:00 / 20:00 the run is silently skipped — and you'll see the yellow ⚠️ "stale" banner on the dashboard the next time you open it.

A companion task **Yad2_Watcher** runs `yad2_watcher.py` hourly: if the last
successful run is more than ~13h old (e.g. the machine was asleep at both
scheduled times) it triggers a catch-up scrape. The single-instance lock keeps it
from colliding with a scheduled or manual run.

---

## Repository

The full source is on GitHub: **[github.com/itailironne/Yad2-Market-Tracker](https://github.com/itailironne/Yad2-Market-Tracker)**
