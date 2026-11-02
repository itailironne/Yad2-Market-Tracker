# Moving the tracker to another PC

The project is self-contained: every script finds its files relative to its own
folder, so the folder can live anywhere on the new machine. What does **not**
travel by itself is the machine setup — Python packages, Google Chrome, and the
three Windows scheduled tasks. `setup_new_pc.ps1` handles that part.

---

## 1. On the OLD PC — stop it

Do this right after a scheduled run finishes (09:00 / 20:00 runs take ~15 min),
so you copy a fresh, consistent snapshot.

1. Make sure no scrape is running: Task Manager → no `python.exe` running
   `yad2_scraper.py`, and no `.yad2_scraper.lock` file in the folder.
2. Disable the scheduled tasks so the two machines never scrape at the same time
   (PowerShell):
   ```powershell
   'Yad2_Morning','Yad2_Evening','Yad2_Watcher' | % { Disable-ScheduledTask -TaskName $_ }
   ```
3. Close the dashboard window(s).

## 2. Copy the folder

Copy the **whole `Yad2_Data` folder** (USB drive, OneDrive, network share).
Don't rely on `git clone` alone — several data files (the listings archives and
some rent files) are not in git.

You can skip these — they are machine-local and get rebuilt automatically:

| Skip | Why |
|---|---|
| `.yad2_chrome_profile\` | Chrome profile holding anti-bot cookies; tied to this machine, re-warmed on the first run |
| `__pycache__\` | Python cache |
| `.yad2_scraper.lock` | Run lock (should not exist if step 1 was done) |
| `*.log` | Old run logs — optional |

## 3. On the NEW PC — install

1. **Python 3.12** from [python.org](https://www.python.org/downloads/).
   In the installer keep **"py launcher"** ticked (also tick "Add python.exe to PATH").
2. **Google Chrome** (the real browser — the scraper uses it to pass Yad2's bot check).
3. Open PowerShell **in the project folder** and run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup_new_pc.ps1
   ```
   This installs the packages from `requirements.txt` and registers the three
   scheduled tasks for the current Windows user, pointing at this folder:

   | Task | Runs | When |
   |---|---|---|
   | `Yad2_Morning` | `yad2_scraper.py` | daily 09:00, wakes the PC |
   | `Yad2_Evening` | `yad2_scraper.py` | daily 20:00, wakes the PC |
   | `Yad2_Watcher` | `yad2_watcher.py` | hourly — catch-up run if data is >13h old |

## 4. Verify

1. Run one scrape by hand and watch it finish:
   ```powershell
   py yad2_scraper.py
   ```
   Expect two Chrome windows (a ~1 min warm-up, then the scrape), and at the end
   `[sale] Saved: ...` and `[rent] Saved: ...`.
2. Double-click **`פתח דשבורד יד2.bat`** — the dashboard opens at
   http://localhost:8501 and the "last updated" time should be a few minutes ago.

## 5. Clean up the old PC

Once the new PC has completed a couple of scheduled runs, delete the tasks on
the old one:

```powershell
'Yad2_Morning','Yad2_Evening','Yad2_Watcher' | % { Unregister-ScheduledTask -TaskName $_ -Confirm:$false }
```

---

## Notes

- **The PC must be logged on** at scrape time (screen locked is fine). The scrape
  opens a visible Chrome window and cannot run in the background without a
  desktop session. Sleep is fine — the tasks wake the machine.
- If the first run fails with a Radware / bot-check error, just run it again — a
  brand-new Chrome profile sometimes needs a second warm-up.
