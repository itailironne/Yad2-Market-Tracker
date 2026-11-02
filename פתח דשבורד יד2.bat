@echo off
cd /d "%~dp0"
start "Yad2 Dashboard" py -m streamlit run yad2_dashboard.py --server.headless true
timeout /t 5 /nobreak >nul
start "" http://localhost:8501
