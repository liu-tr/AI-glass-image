@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM ============================================================
REM  一键启动：先拉起 SD WebUI (A绘世整合包)，等端口就绪后
REM  再启动本项目 Flask 服务。
REM  使用方法：双击本文件即可
REM ============================================================

REM 1) 配置区（按需修改）-----------------------------------
set "SD_LAUNCHER=F:\sd-webui-aki-v4.10\A绘世启动器.exe"
set "SD_HOST=127.0.0.1"
set "SD_PORT=7860"
set "WAIT_TIMEOUT=300"
REM -------------------------------------------------------

echo.
echo ============================================================
echo   玻璃杯 AI 设计系统 — 一键启动 (SD WebUI + Flask)
echo ============================================================
echo.

REM ---- 步骤 1: 检查 SD WebUI 启动器是否存在 ----
if not exist "%SD_LAUNCHER%" (
    echo [错误] 找不到 SD WebUI 启动器: %SD_LAUNCHER%
    echo        请编辑本脚本顶部的 SD_LAUNCHER 变量
    pause
    exit /b 1
)

REM ---- 步骤 2: 检查端口是否已被占用（可能 WebUI 已开着）----
netstat -ano | findstr ":%SD_PORT% " | findstr "LISTENING" >nul
if !errorlevel! equ 0 (
    echo [信息] 端口 %SD_PORT% 已被占用，假定 SD WebUI 已在运行，跳过启动
    goto :wait_flask
)

REM ---- 步骤 3: 拉起 A绘世启动器 ----
echo [步骤 1/4] 启动 A绘世启动器: %SD_LAUNCHER%
echo             请在弹出的窗口里点击"一键启动"按钮
echo.
start "" "%SD_LAUNCHER%"

REM ---- 步骤 4: 轮询端口，等待 WebUI 就绪 ----
echo [步骤 2/4] 等待 SD WebUI 就绪 (端口 %SD_PORT%，最长 %WAIT_TIMEOUT%s)...
set "elapsed=0"
:wait_loop
netstat -ano | findstr ":%SD_PORT% " | findstr "LISTENING" >nul
if !errorlevel! equ 0 goto :webui_ready
if !elapsed! geq %WAIT_TIMEOUT% goto :timeout
REM 还在等：每 5 秒打印一次心跳
set /a mod=!elapsed! %% 5
if !mod! equ 0 echo             等待中... !elapsed!s
timeout /t 1 /nobreak >nul
set /a elapsed+=1
goto :wait_loop

:webui_ready
echo.
echo [信息] SD WebUI 已就绪 (耗时 !elapsed!s)

REM ---- 步骤 5: 额外再探活 /sdapi/v1/options，确保 --api 已开 ----
echo [步骤 3/4] 校验 API 端点 /sdapi/v1/options ...
curl -s -o nul -w "%%{http_code}" --max-time 5 http://%SD_HOST%:%SD_PORT%/sdapi/v1/options > "%TEMP%\sd_probe.txt" 2>nul
set /p SD_CODE=<"%TEMP%\sd_probe.txt"
del "%TEMP%\sd_probe.txt" >nul 2>nul
if "%SD_CODE%"=="200" (
    echo [信息] API 端点正常 ^(HTTP 200^)
) else (
    echo [警告] API 端点返回 HTTP %SD_CODE%
    echo         如果是 404，请确认 webui-user.bat 的 COMMANDLINE_ARGS 含 --api
    echo         脚本会继续启动 Flask，但生图会走 mock 模式
)

:wait_flask
echo.

REM ---- 步骤 6: 切到脚本所在目录并启动 Flask ----
echo [步骤 4/4] 启动 Flask 服务...
cd /d "%~dp0"

REM 复用项目自带的 run.bat（已含依赖检查 / 自动开浏览器）
if exist "run.bat" (
    call run.bat
) else (
    REM 兜底：直接 python app.py
    python app.py
)

echo.
echo Flask 服务已停止。如需重启请再次双击本脚本。
pause
