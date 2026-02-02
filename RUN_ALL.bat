@echo off
chcp 65001 >nul
title TIKTOK SCRAPER
color 0A
echo.
echo ============================================
echo   TIKTOK VIDEO SCRAPER
echo ============================================
echo.
echo Profile: @xoaingotaudio
echo.
echo Doi Chrome mo...
echo.

cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
python tiktok_scraper.py

echo.
echo ============================================
pause
