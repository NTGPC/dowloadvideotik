@echo off
chcp 65001 >nul
title SETUP PLAYWRIGHT
color 0E

echo.
echo ============================================
echo   CAI DAT PLAYWRIGHT
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Kich hoat venv...
call ".venv\Scripts\activate.bat"

echo [2/3] Cai dat Playwright...
pip install playwright pandas openpyxl

echo [3/3] Cai dat Chrome cho Playwright...
playwright install chromium

echo.
echo ============================================
echo   XONG! Bay gio chay: CHAY_PLAYWRIGHT.bat
echo ============================================
pause
