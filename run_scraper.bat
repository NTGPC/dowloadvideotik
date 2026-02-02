@echo off
echo ============================================
echo   CHAY TIKTOK SCRAPER
echo ============================================
echo.

cd /d "%~dp0"

REM Activate venv and run script
call ".venv\Scripts\activate.bat"
python tiktok_scraper.py

echo.
echo ============================================
pause
