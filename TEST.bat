@echo off
chcp 65001 >nul
color 0A
title TEST KET NOI

cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

python test_connection.py

pause
