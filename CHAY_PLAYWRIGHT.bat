@echo off
chcp 65001 >nul
title TIKTOK SCRAPER - PLAYWRIGHT
color 0A

echo.
echo ============================================
echo   TIKTOK SCRAPER - PLAYWRIGHT VERSION
echo ============================================
echo.

cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

python tiktok_playwright.py

echo.
pause
