import asyncio, json, csv, os, re
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
from collections import defaultdict

URL             = "https://www.yad2.co.il/realestate/forsale?city=8700&rooms=4-4"
OUT             = os.path.dirname(os.path.abspath(__file__))
JSON_FILE       = os.path.join(OUT, "yad2_raanana_4rooms.json")
CSV_FILE        = os.path.join(OUT, "yad2_raanana_4rooms.csv")
HISTORY_FILE    = os.path.join(OUT, "yad2_history.csv")
PREV_FILE       = os.path.join(OUT, "yad2_prev_run.json")
FIRST_SEEN_FILE = os.path.join(OUT, "yad2_first_seen.json")
DOM_LOG_FILE    = os.path.join(OUT, "yad2_dom_log.csv")
NB_HISTORY_FILE   = os.path.join(OUT, "yad2_neighborhood_history.csv")
TYPE_HISTORY_FILE = os.path.join(OUT, "yad2_type_history.csv")
RUN_LOG_FILE      = os.path.join(OUT, "yad2_run_log.csv")
DATE_POSTED_FILE  = os.path.join(OUT, "yad2_date_posted.json")

def parse_price_num(p):
    p = str(p).replace(",","").replace("\u20aa","").replace("\u20aa","").strip()
    m = re.search(r"(\d+)", p)
    return int(m.group(1)) if m else None

def parse_yad2_date(text):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", str(text))
    if not m: return ""
    d, mo, y = m.groups()
    if len(y) == 2: y = "20" + y
    try:
        return datetime.strptime(f"{d}/{mo}/{y}", "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return ""

def extract_id_from_url(url):
    """Extract listing ID from a Yad2 URL like .../item/ABC123"""
    clean = url.split("?")[0].rstrip("/")
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
    parts = str(info).split(",")
    return parts[1].strip() if len(parts) > 1 else ""

async def run():
    # ── Shared state needed both inside and after the browser block ───────────
    if os.path.exists(FIRST_SEEN_FILE):
        with open(FIRST_SEEN_FILE, encoding="utf-8") as f:
            first_seen = json.load(f)
    else:
        first_seen = {}
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-cache",
                "--disable-application-cache",
                "--disk-cache-size=0",
                "--media-cache-size=0",
                "--disable-gpu-shader-disk-cache",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL", timezone_id="Asia/Jerusalem",
            viewport={"width": 1280, "height": 800}
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        pg = await context.new_page()
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

        print(datetime.now().strftime("%Y-%m-%d %H:%M"), "- Starting Yad2 scrape...")
        await pg.goto(URL, timeout=60000, wait_until="domcontentloaded")
        await pg.wait_for_timeout(3000)
        while True:
            print("  Page", pnum)
            await pg.wait_for_timeout(2000)

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
                    if url in seen_urls: continue
                    seen_urls.add(url)
                    rooms = floor = size = ""
                    m = re.search(r"(\d+(?:\.\d+)?)\s*\u05d7\u05d3\u05e8", line2)
                    if m: rooms = m.group(1)
                    m = re.search(r"\u05e7\u05d5\u05de\u05d4[^\d]*(\d+)", line2)
                    if m: floor = m.group(1)
                    m = re.search(r"(\d+)\s*\u05de\u05f4\u05e8", line2)
                    if m: size = m.group(1)
                    if price or street:
                        listings.append({"price":price,"street":street,"info":line1,"rooms":rooms,"floor":floor,"size_sqm":size,"url":url,"date_posted":date_posted})
                except: continue
            nb = await pg.query_selector("a[aria-label='\u05e2\u05de\u05d5\u05d3 \u05d4\u05d1\u05d0']")
            if nb and await nb.get_attribute("aria-disabled") != "true":
                await nb.click(); pnum += 1; await pg.wait_for_timeout(3000)
            else: break
        print("Total:", len(listings), "listings")

        # ── Merge fiber-intercepted dates with persistent cache ───────────────
        try:
            with open(DATE_POSTED_FILE, encoding="utf-8") as f:
                date_cache = json.load(f)
        except:
            date_cache = {}

        print(f"  React fiber dates found: {len(intercepted_dates)}")

        # Apply fiber dates to listings
        for r in listings:
            url = r.get("url", "")
            listing_id = extract_id_from_url(url)
            date = intercepted_dates.get(listing_id) or date_cache.get(url, "")
            r["date_posted"] = date
            if date:
                date_cache[url] = date

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
                        date_cache[r["url"]] = d
                        fetched_ok += 1
                if batch_start + batch_size < len(still_missing):
                    print(f"  ...{min(batch_start+batch_size, len(still_missing))}/{len(still_missing)} done")
            print(f"  Got {fetched_ok}/{len(still_missing)} dates via browser fetch")

        # ── Final fallback: use first_seen date when all else fails ─────────
        for r in listings:
            if not r.get("date_posted"):
                url = r.get("url", "")
                fs_date = first_seen.get(url, "") or first_seen.get(url.split("?")[0], "")
                if fs_date:
                    r["date_posted"] = fs_date
                    date_cache[url] = fs_date
                else:
                    r["date_posted"] = today
                    first_seen[url] = today
                    date_cache[url] = today

        matched = sum(1 for r in listings if r.get("date_posted"))
        print(f"  Total dates resolved: {matched}/{len(listings)} listings")
        with open(DATE_POSTED_FILE, "w", encoding="utf-8") as f:
            json.dump(date_cache, f, ensure_ascii=False)

        await browser.close()

    if not listings:
        print("No listings scraped (bot block?). Exiting without overwriting data.")
        return

    curr_map = {r["url"]: r for r in listings if r.get("url")}

    # first_seen was loaded at the start of run() before browser launch

    # ── Load previous run ────────────────────────────────────────────────────
    prev_map = {}
    if os.path.exists(PREV_FILE):
        try:
            with open(PREV_FILE, encoding="utf-8") as f:
                prev_map = {r["url"]: r for r in json.load(f) if r.get("url")}
        except Exception:
            prev_map = {}

    new_urls     = set(curr_map) - set(prev_map)
    removed_urls = set(prev_map) - set(curr_map)
    common_urls  = set(prev_map) & set(curr_map)

    # ── Add new URLs to first_seen ────────────────────────────────────────────
    for url in new_urls:
        first_seen[url] = today

    # ── DOM log for removed listings ──────────────────────────────────────────
    dom_days_list = []
    dom_rows = []
    for url in removed_urls:
        r  = prev_map[url]
        fs = first_seen.get(url, today)
        try:
            dom = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(fs, "%Y-%m-%d")).days
        except:
            dom = 0
        dom_days_list.append(dom)
        nb  = extract_neighborhood(r.get("info",""))
        apt = str(r.get("info","")).split(",")[0].strip() if r.get("info") else ""
        dom_rows.append({
            "removed_date": today,
            "url": url,
            "first_seen": fs,
            "dom_days": dom,
            "price": r.get("price",""),
            "neighborhood": nb,
            "size_sqm": r.get("size_sqm",""),
            "apt_type": apt,
        })
    if dom_rows:
        dom_exists = os.path.exists(DOM_LOG_FILE)
        with open(DOM_LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["removed_date","url","first_seen","dom_days","price","neighborhood","size_sqm","apt_type"])
            if not dom_exists: w.writeheader()
            w.writerows(dom_rows)

    # ── Price changes ─────────────────────────────────────────────────────────
    cuts = rises = 0
    cut_pcts = []
    for url in common_urls:
        pp = parse_price_num(prev_map[url].get("price",""))
        cp = parse_price_num(curr_map[url].get("price",""))
        if pp and cp:
            if cp < pp:
                cuts += 1
                cut_pcts.append((pp - cp) / pp * 100)
            elif cp > pp:
                rises += 1

    # ── Survival rate (30 days) ───────────────────────────────────────────────
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    old_urls = {u for u, d in first_seen.items() if d <= cutoff}
    still_alive = old_urls & set(curr_map)
    survival_30d = round(len(still_alive) / len(old_urls) * 100, 1) if old_urls else None

    # ── Summary stats ─────────────────────────────────────────────────────────
    prices = [parse_price_num(r["price"]) for r in listings]
    prices = [p for p in prices if p]
    sizes  = []
    for r in listings:
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
    absorption   = round(len(removed_urls) / len(prev_map) * 100, 2) if prev_map else 0
    avg_dom      = round(sum(dom_days_list) / len(dom_days_list), 1) if dom_days_list else None

    # ── Append to history CSV ─────────────────────────────────────────────────
    hist_exists = os.path.exists(HISTORY_FILE)
    with open(HISTORY_FILE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not hist_exists:
            w.writerow(["timestamp","count","avg_price","median_price","min_price","max_price",
                        "avg_price_per_sqm","price_cuts","price_rises",
                        "avg_cut_pct","absorption_rate","survival_30d","avg_dom"])
        w.writerow([now, len(listings), avg_price, median_price, min_price, max_price,
                    avg_ppsqm, cuts, rises, avg_cut_pct, absorption,
                    survival_30d if survival_30d is not None else "",
                    avg_dom if avg_dom is not None else ""])

    # ── Neighborhood history ───────────────────────────────────────────────────
    nb_prices = defaultdict(list)
    nb_ppsqm  = defaultdict(list)
    for r in listings:
        nb = extract_neighborhood(r.get("info",""))
        if not nb: continue
        p = parse_price_num(r.get("price",""))
        try: s = float(r.get("size_sqm") or 0)
        except: s = 0
        if p: nb_prices[nb].append(p)
        if p and s: nb_ppsqm[nb].append(p / s)

    nb_exists = os.path.exists(NB_HISTORY_FILE)
    with open(NB_HISTORY_FILE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not nb_exists:
            w.writerow(["timestamp","neighborhood","avg_price","avg_price_per_sqm","count"])
        for nb in nb_prices:
            ppsqm_avg = round(sum(nb_ppsqm[nb]) / len(nb_ppsqm[nb])) if nb_ppsqm.get(nb) else 0
            w.writerow([now, nb, round(sum(nb_prices[nb]) / len(nb_prices[nb])), ppsqm_avg, len(nb_prices[nb])])

    # ── Type history ─────────────────────────────────────────────────────────────
    type_prices = defaultdict(list)
    type_ppsqm  = defaultdict(list)
    for r in listings:
        apt = str(r.get("info","")).split(",")[0].strip() or "דירה"
        p = parse_price_num(r.get("price",""))
        try: s = float(r.get("size_sqm") or 0)
        except: s = 0
        if p: type_prices[apt].append(p)
        if p and s: type_ppsqm[apt].append(p / s)

    type_exists = os.path.exists(TYPE_HISTORY_FILE)
    with open(TYPE_HISTORY_FILE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not type_exists:
            w.writerow(["timestamp","apt_type","avg_price","avg_price_per_sqm","count"])
        for apt in type_prices:
            ppsqm_avg = round(sum(type_ppsqm[apt]) / len(type_ppsqm[apt])) if type_ppsqm.get(apt) else 0
            w.writerow([now, apt, round(sum(type_prices[apt]) / len(type_prices[apt])), ppsqm_avg, len(type_prices[apt])])

    # ── Save files (write to temp then rename so a crash never zeros the file) ──
    import tempfile
    with tempfile.NamedTemporaryFile("w", dir=OUT, suffix=".json", delete=False, encoding="utf-8") as tf:
        json.dump(listings, tf, ensure_ascii=False, indent=2)
        tmp_json = tf.name
    os.replace(tmp_json, JSON_FILE)
    with tempfile.NamedTemporaryFile("w", dir=OUT, suffix=".csv", delete=False,
                                     newline="", encoding="utf-8-sig") as tf:
        w = csv.DictWriter(tf, fieldnames=listings[0].keys())
        w.writeheader(); w.writerows(listings)
        tmp_csv = tf.name
    os.replace(tmp_csv, CSV_FILE)
    with open(PREV_FILE, "w", encoding="utf-8") as f:
        json.dump(listings, f, ensure_ascii=False, indent=2)
    with open(FIRST_SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(first_seen, f, ensure_ascii=False, indent=2)

    print(f"Saved: {len(listings)} listings")
    print(f"New: {len(new_urls)} | Removed: {len(removed_urls)} | Price cuts: {cuts} (avg {avg_cut_pct}%)")
    print(f"Absorption: {absorption}% | Survival 30d: {survival_30d}%")
    if dom_days_list:
        print(f"Avg DOM (removed this run): {avg_dom} days")

    # ── Run log ───────────────────────────────────────────────────────────────
    log_exists = os.path.exists(RUN_LOG_FILE)
    with open(RUN_LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not log_exists:
            w.writerow(["timestamp","status","pages_scraped","total_listings",
                        "new_listings","removed_listings","price_cuts","price_rises",
                        "avg_cut_pct","avg_price","median_price","min_price","max_price",
                        "avg_price_per_sqm","absorption_rate","survival_30d","avg_dom","error"])
        w.writerow([now, "success", pnum - 1, len(listings),
                    len(new_urls), len(removed_urls), cuts, rises,
                    avg_cut_pct, avg_price, median_price, min_price, max_price,
                    avg_ppsqm, absorption,
                    survival_30d if survival_30d is not None else "",
                    avg_dom if avg_dom is not None else "", ""])
    print(f"Run log updated: {RUN_LOG_FILE}")

def log_error(error_msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_exists = os.path.exists(RUN_LOG_FILE)
    with open(RUN_LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not log_exists:
            w.writerow(["timestamp","status","pages_scraped","total_listings",
                        "new_listings","removed_listings","price_cuts","price_rises",
                        "avg_cut_pct","avg_price","median_price","min_price","max_price",
                        "avg_price_per_sqm","absorption_rate","survival_30d","avg_dom","error"])
        w.writerow([now, "error", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", error_msg])

try:
    asyncio.run(run())
except Exception as e:
    print(f"ERROR: {e}")
    log_error(str(e))
