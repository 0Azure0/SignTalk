@echo off
setlocal
title SignTalk - Cloudflare Tunnel

echo ==========================================
echo          SIGNTALK - CLOUDFLARE TUNNEL
echo ==========================================
echo.
echo This window will connect signtalk.com.vn
echo to your local website at http://127.0.0.1:5000
echo.
echo IMPORTANT:
echo 1. Start your SignTalk/Flask website first.
echo 2. Keep the Flask window running.
echo 3. Anyone may be able to access the public website.
echo.

set "CF="

where cloudflared.exe >nul 2>nul
if not errorlevel 1 set "CF=cloudflared.exe"

if not defined CF if exist "%ProgramFiles%\Cloudflare\cloudflared.exe" set "CF=%ProgramFiles%\Cloudflare\cloudflared.exe"
if not defined CF if exist "%ProgramFiles(x86)%\Cloudflare\cloudflared.exe" set "CF=%ProgramFiles(x86)%\Cloudflare\cloudflared.exe"
if not defined CF if exist "%ProgramData%\chocolatey\bin\cloudflared.exe" set "CF=%ProgramData%\chocolatey\bin\cloudflared.exe"
if not defined CF if exist "%LocalAppData%\Programs\cloudflared\cloudflared.exe" set "CF=%LocalAppData%\Programs\cloudflared\cloudflared.exe"

if not defined CF (
  echo ERROR: Windows could not find cloudflared.exe.
  echo.
  echo Open Settings ^> Apps ^> Installed apps and check the Cloudflared entry.
  echo If possible, locate cloudflared.exe in File Explorer.
  echo Then place this BAT file in the same folder as cloudflared.exe and run it again.
  echo.
  pause
  exit /b 1
)

set "CONFIG=%USERPROFILE%\.cloudflared\config.yml"
if not exist "%CONFIG%" (
  echo ERROR: Cloudflare Tunnel config was not found:
  echo "%CONFIG%"
  echo.
  echo Follow the one-time setup instructions in README.md.
  echo.
  pause
  exit /b 1
)

echo Found Cloudflared: "%CF%"
echo.
echo Starting the fixed domain: https://signtalk.com.vn
echo Keep this window open while people are using SignTalk.
echo Press Ctrl+C to stop the tunnel.
echo.
"%CF%" tunnel --config "%CONFIG%" run signtalk

echo.
echo Tunnel has stopped.
pause
