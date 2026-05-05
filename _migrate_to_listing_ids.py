"""One-shot migration: re-key first_seen.json and date_posted.json by listing-ID
instead of full URL.

Why: yad2 attaches randomized query strings (?pagination=…&spot=…&location=…) to
each listing card. Keying by full URL caused the same listing to appear under
~21 different keys on average, which broke new/removed detection, inflated the
absorption rate, and bloated dom_log.csv with spurious removals.

Run once, then commit the rewritten files. Subsequent scraper runs will write
listing-IDs natively.
"""
import json, os, shutil
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))
FIRST_SEEN = os.path.join(DIR, "yad2_first_seen.json")
DATE_POSTED = os.path.join(DIR, "yad2_date_posted.json")


def listing_id(url):
    return (url or "").split("?")[0].rstrip("/").split("/")[-1]


def backup(path):
    if not os.path.exists(path):
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{path}.bak_{stamp}"
    shutil.copy2(path, dst)
    return dst


def migrate_first_seen():
    """URL → ID, keep the EARLIEST first_seen date per listing (oldest is truth)."""
    if not os.path.exists(FIRST_SEEN):
        print(f"  {FIRST_SEEN} missing — skipping")
        return
    bak = backup(FIRST_SEEN)
    with open(FIRST_SEEN, encoding="utf-8") as f:
        old = json.load(f)
    print(f"  first_seen: backed up to {os.path.basename(bak)}")
    print(f"  first_seen: {len(old)} URL-keyed entries")
    if not old:
        return
    # If the first key already looks like a listing-ID (no slash, no '?'), assume migrated.
    sample = next(iter(old))
    if "/" not in sample and "?" not in sample:
        print("  first_seen: already keyed by listing-ID — nothing to do")
        return
    new = {}
    for url, date in old.items():
        lid = listing_id(url)
        if not lid:
            continue
        if lid not in new or (date and date < new[lid]):
            new[lid] = date
    with open(FIRST_SEEN, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)
    print(f"  first_seen: rewrote with {len(new)} listing-ID keys "
          f"(was {len(old)}, ratio {len(old)/max(len(new),1):.1f}x bloat)")


def migrate_date_posted():
    """URL → ID, keep the latest date (yad2-scraped publish date is canonical)."""
    if not os.path.exists(DATE_POSTED):
        print(f"  {DATE_POSTED} missing — skipping")
        return
    bak = backup(DATE_POSTED)
    with open(DATE_POSTED, encoding="utf-8") as f:
        old = json.load(f)
    print(f"  date_posted: backed up to {os.path.basename(bak)}")
    print(f"  date_posted: {len(old)} URL-keyed entries")
    if not old:
        return
    sample = next(iter(old))
    if "/" not in sample and "?" not in sample:
        print("  date_posted: already keyed by listing-ID — nothing to do")
        return
    new = {}
    for url, date in old.items():
        lid = listing_id(url)
        if not lid or not date:
            continue
        # All entries for the same listing should report the same publish date,
        # but in case they don't, keep the earliest (publish date doesn't change).
        if lid not in new or date < new[lid]:
            new[lid] = date
    with open(DATE_POSTED, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False)
    print(f"  date_posted: rewrote with {len(new)} listing-ID keys "
          f"(was {len(old)}, ratio {len(old)/max(len(new),1):.1f}x bloat)")


if __name__ == "__main__":
    print("=" * 60)
    print("  Migrating first_seen.json + date_posted.json to listing-ID keys")
    print("=" * 60)
    migrate_first_seen()
    print()
    migrate_date_posted()
    print("\nDone. Backups created with .bak_<timestamp> suffix.")
