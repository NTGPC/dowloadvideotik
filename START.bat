@echo off
chcp 65001 >nul
title TIKTOK SCRAPER - ALL IN ONE
color 0A

echo.
echo ============================================
echo   TIKTOK VIDEO SCRAPER
echo ============================================
echo.

REM Step 1: Kill Chrome
echo [1/4] Dong tat ca Chrome...
taskkill /F /IM chrome.exe 2>nul
timeout /t 3 /nobreak >nul

REM Step 2: Launch Chrome with debugging
echo [2/4] Mo Chrome voi debugging...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --new-window https://www.tiktok.com
echo      Cho Chrome khoi dong...
timeout /t 10 /nobreak >nul

REM Step 3: Activate venv and run scraper
echo.
echo [3/4] Chay scraper...
echo.
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM Run Python script
python tiktok_scraper.py

REM Step 4: Done
echo.
echo [4/4] Xong!
echo.
pause
