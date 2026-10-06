@echo off
REM ==========================================================
REM  NetOps one-time setup (Windows)
REM  Creates venv, installs Django, migrates, seeds demo data,
REM  runs checks and tests. Output is saved to logs\setup_log.txt
REM ==========================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
echo Running NetOps setup... please wait (this can take 1-2 minutes).
call :main > "logs\setup_log.txt" 2>&1
echo.
echo Finished. Results are in logs\setup_log.txt
timeout /t 8
exit /b

:main
echo === NetOps setup %date% %time% ===
echo --- Tools found ---
where python
where py
where git
python --version
git --version
echo --- Creating virtual environment ---
if not exist venv\Scripts\python.exe (
    python -m venv venv
)
if not exist venv\Scripts\python.exe (
    echo ERROR: virtual environment was not created. Is Python installed and on PATH?
    exit /b 1
)
venv\Scripts\python.exe --version
echo --- Installing dependencies ---
venv\Scripts\python.exe -m pip install --upgrade pip --quiet
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m pip freeze
echo --- Migrations ---
venv\Scripts\python.exe manage.py makemigrations monitoring
venv\Scripts\python.exe manage.py migrate
echo --- Demo data ---
venv\Scripts\python.exe manage.py seed_demo
echo --- Admin user (local only) ---
if exist _local_create_admin.bat call _local_create_admin.bat
echo --- System check ---
venv\Scripts\python.exe manage.py check
echo --- Automated tests ---
venv\Scripts\python.exe manage.py test monitoring -v 2
echo === SETUP FINISHED %time% ===
exit /b 0
