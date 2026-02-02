@echo off
chcp 65001 >nul
title COPY CHROME PROFILE
color 0E

echo.
echo ============================================
echo   COPY CHROME PROFILE DA DANG NHAP
echo ============================================
echo.
echo Script se copy profile Chrome hien tai
echo (da dang nhap TikTok) de su dung
echo.

REM Get username
for /f "tokens=*" %%a in ('whoami') do set USERNAME=%%a
for /f "tokens=2 delims=\" %%a in ("%USERNAME%") do set USERNAME=%%a

set SOURCE=C:\Users\%USERNAME%\AppData\Local\Google\Chrome\User Data\Default
set DEST=%~dp0chrome_profile\Default

echo Nguon: %SOURCE%
echo Dich: %DEST%
echo.

REM Close all Chrome first
echo [1/3] Dong tat ca Chrome...
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

REM Create destination folder
echo [2/3] Tao thu muc...
if not exist "%~dp0chrome_profile" mkdir "%~dp0chrome_profile"

REM Copy profile
echo [3/3] Dang copy profile (co the mat vai phut)...
xcopy "%SOURCE%" "%DEST%" /E /I /H /Y >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo   THANH CONG!
    echo   Profile da duoc copy
    echo   Bay gio chay: CHAY.bat
    echo ============================================
) else (
    echo.
    echo ============================================
    echo   LOI! Khong copy duoc
    echo   Thu chay lai voi quyen Admin
    echo ============================================
)

echo.
pause
