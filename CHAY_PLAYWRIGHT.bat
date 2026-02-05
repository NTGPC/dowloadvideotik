@echo off
chcp 65001 >nul
title TIKTOK MANAGER PRO - UPDATE
color 0A

cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

echo.
echo =====================================================
echo   DANG CAP NHAT THU VIEN (OPENPYXL, PANDAS...)
echo   Vui long doi mot chut...
echo =====================================================
echo.

REM --- CÂU LỆNH NÀY SẼ TỰ ĐỘNG NÂNG CẤP OPENPYXL LÊN BẢN MỚI NHẤT ---
pip install --upgrade openpyxl pandas xlsxwriter yt-dlp PyQt6 playwright
REM ------------------------------------------------------------------

echo.
echo =====================================================
echo   CAP NHAT XONG! DANG MO APP...
echo =====================================================

python tiktok_gui.py

echo.
pause
