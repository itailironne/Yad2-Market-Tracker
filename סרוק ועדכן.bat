@echo off
rem Manual scan: scrape Yad2 (sale + rent), then open the dashboard with the fresh data.
rem Safe to run any time: if a scheduled scrape is already running, the scraper's
rem lock makes this one exit immediately instead of colliding with it.
cd /d "%~dp0"
title Yad2 - scanning
echo.
echo  Scanning Yad2 (sale + rent). This takes about 10-15 minutes.
echo  Chrome windows will open and close by themselves - leave them alone.
echo.
py -u yad2_scraper.py
echo.
rem Start the dashboard only if nothing is listening on its port yet.
powershell -NoProfile -Command "if (-not (Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue)) { exit 1 }"
if errorlevel 1 (
    start "Yad2 Dashboard" /min py -m streamlit run yad2_dashboard.py --server.headless true
    "%SystemRoot%\System32\timeout.exe" /t 6 /nobreak >nul
)
start "" http://localhost:8501
echo  Done. The dashboard is open with the new data.
"%SystemRoot%\System32\timeout.exe" /t 8