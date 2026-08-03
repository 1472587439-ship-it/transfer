@echo off
REM ============================================================
REM  All-Stack Start Script
REM  Launches 4 services in 4 separate windows:
REM    1. "Ozon"          -> Flask server (port 5000)
REM    2. "Crawler"       -> Ozon crawler (daemon mode)
REM    3. "WB-Backend"    -> Spring Boot (port 8080)
REM    4. "WB-Frontend"   -> Vite dev server (port 5173)
REM
REM  Stop: run all-stop.bat
REM  Python-only debug: python-start.bat
REM ============================================================

setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo.
echo ==========================================================
echo   All-Stack Start
echo   Project: %cd%
echo ==========================================================
echo.
echo   4 windows will open:
echo     [Ozon]         Flask 5000
echo     [Crawler]      crawler (output)
echo     [WB-Backend]   Spring Boot 8080
echo     [WB-Frontend]  Vite 5173
echo.

REM ---------- 1. Environment checks ----------
echo [1/6] Checking Python ...
where python >nul 2>nul
if errorlevel 1 (
    echo   [X] python not found, install Python 3.10+
    pause > nul
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   [OK] Python %%v

echo [2/6] Checking Node.js ...
where node >nul 2>nul
if errorlevel 1 (
    echo   [X] node not found, install Node.js 18+ https://nodejs.org/
    pause > nul
    exit /b 1
)
for /f "tokens=1" %%v in ('node -v') do echo   [OK] Node %%v

echo [3/6] Checking Java ...
where java >nul 2>nul
if errorlevel 1 (
    echo   [X] java not found, install JDK 17+ and set JAVA_HOME
    pause > nul
    exit /b 1
)
for /f "tokens=3" %%v in ('java -version 2^>^&1 ^| findstr /i "version"') do echo   [OK] Java %%v

echo [4/6] Checking Maven Wrapper ...
if not exist "mvnw.cmd" (
    echo   [X] mvnw.cmd not found, run from project root
    pause > nul
    exit /b 1
)
echo   [OK] mvnw.cmd ready

echo [5/6] Checking Python deps ...
if not exist ".venv" (
    if not exist "requirements.txt" (
        echo   [X] requirements.txt not found, run from project root
        pause > nul
        exit /b 1
    )
    echo   [i] .venv not found, please run manually:
    echo       python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
    echo   [i] Continuing anyway (Python parts may fail, Java parts will still work)
) else (
    echo   [OK] .venv ready
)

echo [6/6] Checking frontend deps ...
if not exist "frontend\node_modules" (
    echo   [!] frontend\node_modules missing, running npm install ...
    pushd frontend
    call npm install
    if errorlevel 1 (
        echo   [X] npm install failed, check network or run manually
        popd
        pause > nul
        exit /b 1
    )
    popd
)
echo   [OK] frontend deps ready

REM ---------- 2. Pre-clean ports ----------
REM Safely kill only our own services on these ports (python / java / node).
REM Calls a standalone .ps1 script to avoid cmd/powershell quote-escaping issues.
REM Does NOT affect unrelated processes even if they use these ports.
echo.
echo ==========================================================
echo   Cleaning ports 5000 / 8080 / 5173
echo ==========================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kill-ports.ps1"
timeout /t 1 /nobreak >nul

REM ---------- 3. Launch Python stack (Ozon + Crawler) ----------
echo.
echo ==========================================================
echo   Launching Python stack (2 windows)
echo ==========================================================

echo   [1/4] starting Flask (Ozon) ...
start "Ozon" cmd /k "python server.py"

timeout /t 2 /nobreak >nul

echo   [2/4] starting Crawler ...
start "Crawler" cmd /k "python crawler.py --folder output --daemon"

REM ---------- 4. Launch Java backend ----------
echo   [3/4] starting Spring Boot (WB-Backend) ...
start "WB-Backend" cmd /k "cd /d %cd% && mvnw.cmd spring-boot:run"

REM ---------- 5. Launch frontend ----------
echo   [4/4] starting Vite (WB-Frontend) ...
start "WB-Frontend" cmd /k "cd /d %cd%\frontend && npm run dev"

REM ---------- 6. Wait for backend, then open browser ----------
echo.
echo ==========================================================
echo   Waiting for backend (up to 45s) ...
echo ==========================================================

set /a TRY=0
:WAIT_BACKEND
set /a TRY+=1

powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue; if ($c) { exit 0 } else { exit 1 }" >nul 2>&1

if %ERRORLEVEL% EQU 0 goto :BACKEND_READY

if %TRY% GEQ 15 (
    echo   [!] backend not ready after 45s, opening browser anyway (may show 502)
    goto :OPEN_BROWSER
)
timeout /t 3 /nobreak >nul
goto :WAIT_BACKEND

:BACKEND_READY
echo   [+] backend ready (port 8080)

:OPEN_BROWSER
echo   opening browser: http://localhost:5000 and http://localhost:5173
start "" "http://localhost:5000"
timeout /t 1 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo ==========================================================
echo   All services launched.
echo   - Ozon         Flask 5000
echo   - Crawler      crawler (output)
echo   - WB-Backend   Spring Boot 8080
echo   - WB-Frontend  Vite 5173
echo.
echo   To stop everything, run all-stop.bat
echo   Python-only debug: python-start.bat
echo ==========================================================
echo.
echo   (this window will auto-close in 60s, or press any key to close now)
echo   4 service windows are still running in background.
echo.
powershell -NoProfile -Command "$h = $Host.UI.RawUI; $deadline = (Get-Date).AddSeconds(60); while ((Get-Date) -lt $deadline) { if ($h.KeyAvailable) { exit 0 }; Start-Sleep -Milliseconds 200 }; exit 0"
endlocal
