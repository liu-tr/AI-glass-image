@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Glass AI Design System

echo ============================================
echo    Glass Cup AI Visualization Design System
echo ============================================
echo.

REM 1. Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python and add it to PATH.
    echo.
    pause
    exit /b 1
)

REM 2. Check dependencies, install if missing
python -c "import flask, flask_cors, numpy, requests" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Missing dependencies detected. Installing from requirements.txt ...
    python -m pip install -r requirements.txt
    echo.
)

REM 3. Check SD WebUI status (port 7860 + /sdapi/v1/options)
echo [STEP 3/4] Checking SD WebUI status ...
echo --------------------------------------------
netstat -ano | findstr ":7860" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [WARN] SD WebUI is NOT running on port 7860.
    echo        Flask will start in MOCK mode ^(placeholder images^).
    echo.
    echo        To enable real AI generation:
    echo          1. Open the A-shih launcher on your Desktop.
    echo          2. Make sure "--api" is checked in Advanced Options.
    echo          3. Click "One-click start" and wait for "Running on local URL: 7860".
    echo.
    echo Waiting up to 60 seconds for SD WebUI to come online ...
    echo ^(Press Ctrl+C to skip and continue with mock mode^)
    echo.
) else (
    echo [OK] Port 7860 in use, verifying API endpoint ...
    curl -s -o nul -w "%%{http_code}" --max-time 3 http://127.0.0.1:7860/sdapi/v1/options > "%TEMP%\sdcode.txt" 2>nul
    set /p SDCODE=<"%TEMP%\sdcode.txt"
    del "%TEMP%\sdcode.txt" >nul 2>nul
    if "!SDCODE!"=="200" (
        echo [OK] SD WebUI API ready. Will use REAL image generation.
    ) else (
        echo [WARN] Port in use but API returned HTTP !SDCODE!. Flask will use MOCK mode.
        echo        Add "--api" to SD WebUI startup args.
    )
    echo.
)

REM 4. Wait for SD WebUI to come online (up to 60s, polls every 2s)
echo [STEP 4/4] Waiting for SD WebUI on http://127.0.0.1:7860/sdapi/v1/options
echo            ^(Press Ctrl+C to abort and start Flask anyway^)
echo.
set /a WAITED=0

:WAIT_LOOP
netstat -ano | findstr ":7860" | findstr "LISTENING" >nul
if not errorlevel 1 (
    curl -s -o nul -w "%%{http_code}" --max-time 2 http://127.0.0.1:7860/sdapi/v1/options > "%TEMP%\sdcode2.txt" 2>nul
    set /p SDCODE2=<"%TEMP%\sdcode2.txt"
    del "%TEMP%\sdcode2.txt" >nul 2>nul
    if "!SDCODE2!"=="200" (
        echo.
        echo [OK] SD WebUI is now ready!
        goto :SD_READY
    )
)
if !WAITED! GEQ 60 (
    echo.
    echo [TIMEOUT] SD WebUI did not respond within 60 seconds.
    echo           Flask will start in MOCK mode.
    goto :SD_READY
)
set /a WAITED+=2
echo   ... waiting !WAITED!s / 60s
ping -n 3 127.0.0.1 >nul
goto :WAIT_LOOP

:SD_READY
echo.
echo Starting backend server ...
echo Browser will open http://localhost:5000 automatically once ready.
echo Close this window or press Ctrl+C to stop the server.
echo.

REM 5. Wait for Flask to be ready, then open default browser
start "" powershell -WindowStyle Hidden -Command "for($i=0;$i -lt 30;$i++){try{Invoke-WebRequest 'http://localhost:5000' -UseBasicParsing -TimeoutSec 1 | Out-Null; break}catch{Start-Sleep -Milliseconds 500}}; Start-Process 'http://localhost:5000'"

REM 6. Start Flask in foreground (shows live logs)
python app.py

echo.
echo Server stopped.
pause
