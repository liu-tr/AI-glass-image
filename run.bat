@echo off
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

echo Starting backend server...
echo Browser will open http://localhost:5000 automatically once ready.
echo Close this window or press Ctrl+C to stop the server.
echo.

REM 3. Wait for server to be ready in background, then open default browser
start "" powershell -WindowStyle Hidden -Command "for($i=0;$i -lt 30;$i++){try{Invoke-WebRequest 'http://localhost:5000' -UseBasicParsing -TimeoutSec 1 | Out-Null; break}catch{Start-Sleep -Milliseconds 500}}; Start-Process 'http://localhost:5000'"

REM 4. Start Flask in foreground (shows live logs)
python app.py

echo.
echo Server stopped.
pause
