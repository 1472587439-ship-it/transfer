@echo off
REM ============================================================
REM  All-Stack Stop Script
REM  Closes 4 service windows: Ozon / Crawler / WB-Backend / WB-Frontend
REM  Then kills residual processes on ports 5000 / 8080 / 5173
REM ============================================================

setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo.
echo ==========================================================
echo   All-Stack Stop
echo ==========================================================
echo.

REM ---------- 1. Kill by window title ----------
REM We only kill windows whose title exactly matches our 4 service titles.
REM Using exact match (no wildcard) so a folder named "Ozon" does NOT match.
REM This never affects Explorer because Explorer titles are full paths like "C:\Users\...".
echo [1/4] Closing "Ozon" window ...
taskkill /F /FI "WINDOWTITLE eq Ozon"         >nul 2>nul
echo [2/4] Closing "Crawler" window ...
taskkill /F /FI "WINDOWTITLE eq Crawler"     >nul 2>nul
echo [3/4] Closing "WB-Backend" window ...
taskkill /F /FI "WINDOWTITLE eq WB-Backend"  >nul 2>nul
echo [4/4] Closing "WB-Frontend" window ...
taskkill /F /FI "WINDOWTITLE eq WB-Frontend" >nul 2>nul
echo   [OK] Window cleanup done

REM ---------- 2. Kill residual processes by port ----------
REM Only kill processes matching our expected service names (python / java / node).
REM Calls a standalone .ps1 script to avoid cmd/powershell quote-escaping issues.
REM Does NOT kill unrelated services even if they happen to use these ports.
echo [2/3] Checking and killing listeners on ports 5000 / 8080 / 5173 ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kill-ports.ps1"

REM ---------- 3. Cleanup complete ----------
echo [3/3] Cleanup done

echo.
echo ==========================================================
echo   All services stopped.
echo   - To restart, run all-start.bat
echo   - Python-only debug: python-start.bat
echo ==========================================================
echo.
echo   (this window will auto-close in 30s, or press any key to close now)
echo.
powershell -NoProfile -Command "$h = $Host.UI.RawUI; $deadline = (Get-Date).AddSeconds(30); while ((Get-Date) -lt $deadline) { if ($h.KeyAvailable) { exit 0 }; Start-Sleep -Milliseconds 200 }; exit 0"
endlocal
