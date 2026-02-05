@echo off
chcp 65001 >nul
title TIKTOK FULL AUTOMATION
color 0A

cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM --- TỰ ĐỘNG CÀI CÁC THƯ VIỆN CẦN THIẾT ---
pip install xlsxwriter yt-dlp
REM ------------------------------------------

python tiktok_playwright.py

echo.
pause
