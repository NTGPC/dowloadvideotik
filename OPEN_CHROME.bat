@echo off
chcp 65001 >nul
color 0C
title BUOC 1 - DONG VA MO CHROME

echo.
echo ============================================
echo   BUOC 1: DONG VA MO CHROME
echo ============================================
echo.

echo [1/4] KILL CHROME LAN 1...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/4] KILL CHROME LAN 2 (DAM BAO)...
taskkill /F /IM chrome.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [3/4] MO CHROME MOI (debugging port 9222)...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\tiktok_chrome" https://www.tiktok.com

echo [4/4] DOI 15 GIAY CHO CHROME VA PORT...
timeout /t 15 /nobreak >nul

echo.
echo ============================================
echo   XONG! BAY GIO CHAY: TEST.bat
echo   Neu TEST.bat bao "SAN SANG" thi chay RUN_ALL.bat
echo ============================================
echo.
pause
