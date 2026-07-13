@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM  One-click launcher: start SD WebUI first, wait for port,
REM  then start Flask.
REM  Usage: double-click this file
REM ============================================================

REM --- Config (edit if needed) ---
set "SD_LAUNCHER=F:\sd-webui-aki-v4.10\A»æÊÀÆô¶¯Æ÷.exe"
set "SD_PORT=7860"
set "WAIT_TIMEOUT=300"
REM ---------------------------------

echo.
echo ============================================================
echo   Glass Cup AI Design System - One-click Launcher
echo ============================================================
echo.
echo Launcher: %SD_LAUNCHER%
echo.

REM Step 1: check launcher exists
if not exist "%SD_LAUNCHER%" (
    echo [ERROR] SD WebUI launcher not found: %SD_LAUNCHER%
    echo         Edit SD_LAUNCHER at the top of this script.
    pause
    exit /b 1
)

REM Step 2: check if port already taken
netstat -ano | findstr ":%SD_PORT% " | findstr "LISTENING" >nul
if !errorlevel! equ 0 (
    echo [INFO] Port %SD_PORT% already in use, assume WebUI is running.
    goto :wait_flask
)

REM Step 3: launch
echo [1/4] Launching ...
echo         Please click "One-click start" in the popup window.
echo.
start "" "%SD_LAUNCHER%"

REM Step 4: poll port
echo [2/4] Waiting for SD WebUI on port %SD_PORT% (max %WAIT_TIMEOUT%s)...
set "elapsed=0"
:wait_loop
netstat -ano | findstr ":%SD_PORT% " | findstr "LISTENING" >nul
if !errorlevel! equ 0 goto :webui_ready
if !elapsed! geq %WAIT_TIMEOUT% goto :timeout
set /a mod=!elapsed! %% 5
if !mod! equ 0 echo         waiting... !elapsed!s
timeout /t 1 /nobreak >nul
set /a elapsed+=1
goto :wait_loop

:webui_ready
echo.
echo [INFO] SD WebUI ready (took !elapsed!s)

REM Step 5: probe API
echo [3/4] Probing API endpoint /sdapi/v1/options ...
curl -s -o nul -w "%%{http_code}" --max-time 5 http://127.0.0.1:%SD_PORT%/sdapi/v1/options > "%TEMP%\sd_probe.txt" 2>nul
set /p SD_CODE=<"%TEMP%\sd_probe.txt"
del "%TEMP%\sd_probe.txt" >nul 2>nul
if "%SD_CODE%"=="200" (
    echo [INFO] API OK (HTTP 200)
) else (
    echo [WARN] API returned HTTP %SD_CODE%
    echo        If 404: add --api to webui-user.bat COMMANDLINE_ARGS, restart WebUI.
    echo        Flask will start in mock mode.
)

:wait_flask
echo.

REM Step 6: start Flask
echo [4/4] Starting Flask ...
cd /d "%~dp0"

if exist "run.bat" (
    call run.bat
) else (
    python app.py
)

echo.
echo Flask stopped. Run this script again to restart.
pause
