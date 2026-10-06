@echo off
REM ==========================================================
REM  Start the NetOps development server and open the browser.
REM  Stop the server with CTRL+C (or close this window).
REM ==========================================================
chcp 65001 >nul
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
    echo Virtual environment not found. Run setup_netops.bat first.
    pause
    exit /b 1
)
echo Starting NetOps at http://127.0.0.1:8000/
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000/"
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
pause
