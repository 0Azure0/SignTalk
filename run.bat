@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay Python trong moi truong ao .venv.
    echo Hay tao moi truong .venv va cai requirements.txt truoc.
    pause
    exit /b 1
)

echo Dang khoi dong SignTalk...
".venv\Scripts\python.exe" main.py

echo.
echo SignTalk da dung hoac gap loi.
pause