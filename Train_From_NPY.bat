@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"

cd /d "%ROOT%" || goto failed

if not exist "%PYTHON%" (
    echo [LOI] Khong tim thay Python trong .venv.
    echo Hay tao moi truong .venv va cai requirements.txt truoc.
    goto failed
)

if not exist "%ROOT%data\*.npy" (
    echo [LOI] Khong tim thay file .npy trong thu muc data.
    echo Hay chay Cache_Videos_To_NPY.bat truoc.
    goto failed
)

"%PYTHON%" scripts\train.py --model_name vsl_model --data_only
if errorlevel 1 goto failed

echo.
echo Train thanh cong. Model duoc luu tai models\vsl_model.pkl
pause
exit /b 0

:failed
echo.
echo Train that bai. Kiem tra log phia tren.
pause
exit /b 1
