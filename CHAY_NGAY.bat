@echo off
chcp 65001 >nul
title TIKTOK SCRAPER - SIMPLE
color 0A

echo.
echo ============================================
echo   TIKTOK VIDEO SCRAPER - PHIEN BAN DON GIAN
echo ============================================
echo.
echo Script se tu dong mo Chrome moi
echo Ban chi can dang nhap TikTok khi duoc yeu cau
echo.
pause

cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
python tiktok_scraper.py

echo.
echo ============================================
pause
