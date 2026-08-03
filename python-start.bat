@echo off
REM ============================================================
REM  Python-Only Start Script
REM  Launches only Ozon (Flask 5000) + Crawler.
REM  Use this when debugging Python parts without Java backend.
REM  For full stack, use all-start.bat.
REM
REM  Stop: run all-stop.bat (works on window titles Ozon / Crawler)
REM  Note: Chinese text removed to avoid chcp 65001 / cmd parsing bugs.
REM ============================================================

setlocal ENABLEEXTENSIONS
cd /d "%~dp0"

cls
echo.
echo ==========================================================
echo   Python-Only Start
echo ==========================================================
echo.
echo   [1/3] Starting Flask server (server.py)...
echo   [2/3] Starting crawler (crawler.py --folder output --daemon)...
echo   [3/3] Waiting for Flask, then opening browser...
echo.
echo   To stop:
echo     - Run all-stop.bat, or
echo     - Ctrl+C in each service window
echo ==========================================================
echo.

REM ------------------------------------------------------------
REM  Flask server in independent window titled "Ozon"
REM ------------------------------------------------------------
start "Ozon" cmd /k "python server.py"

REM brief pause to avoid resource contention
timeout /t 2 /nobreak >nul

REM ------------------------------------------------------------
REM  Crawler in independent window titled "Crawler"
REM ------------------------------------------------------------
start "Crawler" cmd /k "python crawler.py --folder output --daemon"

REM ------------------------------------------------------------
REM  Wait for Flask to come up before opening browser.
REM  Flask listens on 5000, poll up to 15s with 3s interval.
REM ------------------------------------------------------------
echo [*] waiting for Flask (up to 15s) ...

set /a TRY=0
:WAIT_LOOP
set /a TRY+=1

powershell -NoProfile -Command ^
  "$c = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue; if ($c) { exit 0 } else { exit 1 }" >nul 2>&1

if %ERRORLEVEL% EQU 0 goto :READY

if %TRY% GEQ 5 (
    echo [!] Flask not ready after 15s, opening browser anyway (may show 502)
    goto :OPEN_BROWSER
)
timeout /t 3 /nobreak >nul
goto :WAIT_LOOP

:READY
echo [+] Flask ready (port 5000)

:OPEN_BROWSER
start "" "http://localhost:5000"

echo.
echo ==========================================================
echo   Done.
echo.
echo   Frontend:    http://localhost:5000
echo   Window 1:    "Ozon"
echo   Window 2:    "Crawler"
echo.
echo   - Refresh browser after editing frontend code
echo   - Crawler output is in output\ folder
echo   - You can close this window; services keep running
echo ==========================================================
echo.
echo   (auto-close in 60s, or press any key to close now)
echo.
powershell -NoProfile -Command "$h = $Host.UI.RawUI; $deadline = (Get-Date).AddSeconds(60); while ((Get-Date) -lt $deadline) { if ($h.KeyAvailable) { exit 0 }; Start-Sleep -Milliseconds 200 }; exit 0"
endlocal
exit /b 0
