@echo off
setlocal

set "ROOT=%~dp0"
set "VIDEOS_DIR=%ROOT%videos"
set "DATA_DIR=%ROOT%data"
set "CACHE_DIR=%ROOT%processed\video_npy_cache"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"

cd /d "%ROOT%" || goto failed

if not exist "%PYTHON%" (
    echo [LOI] Khong tim thay Python trong .venv.
    echo Hay tao moi truong .venv va cai requirements.txt truoc.
    goto failed
)

if not exist "%VIDEOS_DIR%\" (
    echo [LOI] Khong tim thay thu muc videos.
    goto failed
)

if not exist "%CACHE_DIR%\" mkdir "%CACHE_DIR%"

dir /b /ad "%VIDEOS_DIR%" >nul 2>nul
if errorlevel 1 (
    echo [LOI] Khong co thu muc lop nao trong videos.
    goto failed
)

for /d %%D in ("%VIDEOS_DIR%\*") do (
    call :cache_class "%%~fD" "%%~nxD"
    if errorlevel 1 goto failed
)

echo.
echo Da cache xong cac lop video chua xu ly.
echo Chay Train_From_NPY.bat de huan luyen model.
pause
exit /b 0

:failed
echo.
echo Cache video that bai. Kiem tra log phia tren.
pause
exit /b 1

:cache_class
set "CLASS_DIR=%~1"
set "CLASS_NAME=%~2"
set "HAS_VIDEO="

for %%E in (mp4 avi mov mkv webm wmv) do (
    if exist "%CLASS_DIR%\*.%%E" set "HAS_VIDEO=1"
)

if not defined HAS_VIDEO (
    echo [BO QUA] %CLASS_NAME% khong co video ho tro.
    exit /b 0
)

if exist "%CACHE_DIR%\%CLASS_NAME%.done" (
    echo [BO QUA] %CLASS_NAME% da duoc cache.
    exit /b 0
)

echo.
echo [DANG XU LY] %CLASS_NAME%
"%PYTHON%" scripts\video_to_data.py --input "%CLASS_DIR%" --pose_name "%CLASS_NAME%" --step 2 --append
if errorlevel 1 exit /b 1
if not exist "%DATA_DIR%\%CLASS_NAME%.npy" (
    echo [LOI] Khong tao duoc data\%CLASS_NAME%.npy.
    exit /b 1
)
>"%CACHE_DIR%\%CLASS_NAME%.done" echo Cached
exit /b 0
