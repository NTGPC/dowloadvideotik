@echo off
chcp 65001 >nul
title TIKTOK SCRAPER
color 0A

echo.
echo ============================================
echo   TIKTOK VIDEO SCRAPER
echo ============================================
echo.

cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

echo Dang chay scraper...
echo.
python tiktok_scraper.py

echo.
echo ============================================
pause
