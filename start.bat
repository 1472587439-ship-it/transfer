@echo off
REM ============================================================
REM  一键启动器 - 同时启动 Ozon 服务 + 爬虫, 并打开前端页面
REM ============================================================
REM  用法: 直接双击 start.bat, 或在 cmd 里执行 start.bat
REM  关闭: 关闭爬虫窗口 (Cmd 里 Ctrl+C 后输入 y 回车),
REM        关闭服务窗口同理
REM ============================================================

setlocal ENABLEEXTENSIONS

REM 切到脚本所在目录 (从快捷方式/资源管理器启动也保证正确)
cd /d "%~dp0"

cls
echo ============================================================
echo   Ozon 一键启动器
echo ============================================================
echo.
echo   [1/3] 启动 Flask 服务 (server.py)...
echo   [2/3] 启动爬虫 (crawler.py --folder output --d)...
echo   [3/3] 等服务起来后自动打开前端页面...
echo.
echo   关闭方式:
echo     - 服务窗口: Ctrl+C 然后回车
echo     - 爬虫窗口: Ctrl+C 然后回车
echo ============================================================
echo.

REM ------------------------------------------------------------
REM 启动 Flask 服务 - 在独立窗口, 标题为 "Ozon 服务"
REM ------------------------------------------------------------
start "Ozon 服务" cmd /k "python server.py"

REM 短暂停顿避免爬虫抢资源
timeout /t 2 /nobreak >nul

REM ------------------------------------------------------------
REM 启动爬虫 - 在独立窗口, 标题为 "爬虫 (output)"
REM ------------------------------------------------------------
start "爬虫 (output)" cmd /k "python crawler.py --folder output --daemon"

REM ------------------------------------------------------------
REM 等待 Flask 起来再开浏览器
REM  Flask 默认监听 5000, 这里轮询 10 秒, 3 秒间隔后
REM  第一次尝试, 让用户不用等太久
REM ------------------------------------------------------------
echo [*] 等待 Flask 服务就绪 (最多 15 秒)...

set /a TRY=0
:WAIT_LOOP
set /a TRY+=1

REM 用 powershell 探测端口, 比单纯 sleep 更稳
powershell -NoProfile -Command ^
  "$c = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue; if ($c) { exit 0 } else { exit 1 }" >nul 2>&1

if %ERRORLEVEL% EQU 0 goto :READY

if %TRY% GEQ 5 (
    echo [!] Flask 15 秒内未起来, 仍尝试打开浏览器 (可能 502)
    goto :OPEN_BROWSER
)
timeout /t 3 /nobreak >nul
goto :WAIT_LOOP

:READY
echo [+] Flask 服务已起来 (端口 5000)

:OPEN_BROWSER
REM 用 start "" 避免 "http://..." 被当成窗口标题
start "" "http://localhost:5000"

echo.
echo ============================================================
echo   启动完成!
echo.
echo   前端页面:   http://localhost:5000
echo   服务窗口:   "Ozon 服务"
echo   爬虫窗口:   "爬虫 (output)"
echo.
echo   - 修改前端代码后刷新浏览器即可
echo   - 爬虫报告产出在 output\ 文件夹
echo   - 这个窗口可以关闭, 不影响服务运行
echo ============================================================
echo.
endlocal
exit /b 0
