@echo off
setlocal
cd /d "C:\app\SignTalk"

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay Python trong moi truong ao .venv.
    echo Hay kiem tra thu muc C:\app\SignTalk\.venv
    pause
    exit /b 1
)

echo Dang khoi dong SignTalk...
".venv\Scripts\python.exe" main.py

echo.
echo SignTalk da dung hoac gap loi.
pause