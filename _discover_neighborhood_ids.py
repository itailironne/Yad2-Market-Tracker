"""One-shot discovery: visit yad2's Ra'anana filter page and extract every
neighborhood's canonical numeric ID. Saves the map to
yad2_neighborhood_ids.json for the main scraper to consume.

Run when yad2 adds/renames neighborhoods; otherwise the cached JSON is used.

Strategy:
  1. Open the city URL.
  2. Capture every JSON network response and scan for objects that look like
     {name/text: "<Hebrew name>", id/value: <int>} — yad2 fetches the dropdown
     options from an API.
  3. As a fallback, click the neighborhood filter button and read the
     options from the DOM.
"""
import asyncio
import json
import os
import re
import sys

from playwright.async_api import async_playwright

OUT = os.path.dirname(os.path.abspath(__file__))
URL = "https://www.yad2.co.il/realestate/forsale?city=8700&rooms=4-4"
OUTFILE = os.path.join(OUT, "yad2_neighborhood_ids.json")
HEBREW = re.compile(r"[֐-׿]")


def looks_like_neighborhood_obj(obj):
    """Detect dict objects that look like {name: <hebrew>, id: <int>}."""
    if not isinstance(obj, dict):
        return None
    name = None
    nid = None
    for k in ("text", "name", "label", "title", "displayName"):
        v = obj.get(k)
        if isinstance(v, str) and HEBREW.search(v):
            name = v.strip()
            break
    for k in ("id", "value", "neighborhood_id", "neighborhoodId", "code"):
        v = obj.get(k)
        if isinstance(v, int) and 1 <= v < 100000:
            nid = v
            break
        if isinstance(v, str) and v.isdigit():
            nid = int(v)
            break
    if name and nid:
        return name, nid
    return None


def harvest(obj, into):
    if isinstance(obj, dict):
        hit = looks_like_neighborhood_obj(obj)
        if hit:
            name, nid = hit
            # avoid recording obvious non-neighborhoods like cities/areas by
            # skipping known city/area names; we'll let the user prune later
            into.setdefault(name, nid)
        for v in obj.values():
            harvest(v, into)
    elif isinstance(obj, list):
        for item in obj:
            harvest(item, into)


async def discover():
    candidates = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="he-IL",
            timezone_id="Asia/Jerusalem",
            viewport={"width": 1280, "height": 900},
        )
        pg = await context.new_page()

        async def on_response(response):
            try:
                ct = response.headers.get("content-type", "")
                if "json" not in ct:
                    return
                if "yad2" not in response.url:
                    return
                body = await response.json()
                harvest(body, candidates)
            except Exception:
                pass

        pg.on("response", on_response)

        print(f"Loading {URL} ...")
        await pg.goto(URL, timeout=60000, wait_until="domcontentloaded")
        await pg.wait_for_timeout(3000)

        # Try clicking the neighborhood filter button to force the dropdown to
        # populate (in case the API call is lazy).
        for sel in (
            'button:has-text("שכונה")',
            '[aria-label*="שכונ"]',
            'button[data-testid*="neighborhood"]',
            '[data-testid="filter-neighborhood"]',
        ):
            try:
                btn = await pg.query_selector(sel)
                if btn:
                    await btn.scroll_into_view_if_needed(timeout=2000)
                    await btn.click(timeout=3000)
                    await pg.wait_for_timeout(1500)
                    break
            except Exception:
                continue

        # Also scan the rendered DOM for neighborhood= hrefs as a third source.
        try:
            anchors = await pg.query_selector_all('a[href*="neighborhood="]')
            for a in anchors:
                href = await a.get_attribute("href") or ""
                m = re.search(r"neighborhood=(\d+)", href)
                if not m:
                    continue
                nid = int(m.group(1))
                name = (await a.inner_text()).strip()
                if name and HEBREW.search(name):
                    candidates.setdefault(name, nid)
        except Exception:
            pass

        await browser.close()

    if not candidates:
        print("No neighborhoods discovered — yad2's UI structure may have changed.")
        print("Open the page manually and inspect the network panel for a JSON")
        print("response containing neighborhood options, or paste the URLs you")
        print("see when filtering by neighborhood and I'll extract IDs from them.")
        sys.exit(1)

    # Strip obvious non-neighborhoods (cities/areas/regions) by IDs we know.
    # Ra'anana's city ID is 8700; area is 42; topArea sometimes appears.
    # If a candidate has the same id as those, drop it.
    KNOWN_NON_NB_IDS = {8700, 42}
    cleaned = {n: i for n, i in candidates.items() if i not in KNOWN_NON_NB_IDS}

    with open(OUTFILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"\nSaved {len(cleaned)} neighborhood IDs to {os.path.basename(OUTFILE)}")
    for name in sorted(cleaned, key=lambda n: cleaned[n]):
        print(f"  {cleaned[name]:>5}  {name}")


if __name__ == "__main__":
    asyncio.run(discover())
