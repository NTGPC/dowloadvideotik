@echo off
echo ============================================
echo   KHOI DONG CHROME VOI REMOTE DEBUGGING
echo ============================================
echo.

REM Kill all Chrome processes first
echo Dang dong tat ca Chrome...
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

echo Dang khoi dong Chrome voi remote debugging...
echo.

REM Start Chrome with remote debugging (uses default profile)
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

echo.
echo ============================================
echo   Chrome da san sang!
echo ============================================
echo.
echo Hay dang nhap TikTok trong Chrome
echo Sau do chay script tiktok_scraper.py
echo.
echo Nhan phim bat ky de dong cua so nay...
pause >nul
