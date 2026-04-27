@echo off
cd /d "C:\Users\Ayelet Lironne\Yad2_Data"
start "Yad2 Dashboard" "C:\Users\Ayelet Lironne\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run yad2_dashboard.py --server.headless true
timeout /t 5 /nobreak >nul
start "" http://localhost:8501
