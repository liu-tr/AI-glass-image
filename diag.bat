@echo off
setlocal

echo ============================================================
echo   Glass Cup AI - 30s Diagnostic Check
echo ============================================================
echo.

REM 1) Port and process check
echo [1/3] Ports and processes
echo ----------------------------------------
netstat -ano | findstr ":5000" | findstr "LISTENING"
if errorlevel 1 echo   5000  : [NOT LISTENING] Flask not started
netstat -ano | findstr ":7860" | findstr "LISTENING"
if errorlevel 1 echo   7860  : [NOT LISTENING] SD WebUI not started
echo.
echo Active python.exe processes:
tasklist /FI "IMAGENAME eq python.exe" 2>nul | findstr /V "INFO:"
echo.

REM 2) Probe live endpoints
echo [2/3] Endpoint probe
echo ----------------------------------------
curl -s -o nul -w "%%{http_code}" --max-time 3 http://127.0.0.1:5000/ > "%TEMP%\fc.txt" 2>nul
set /p FC=<"%TEMP%\fc.txt"
del "%TEMP%\fc.txt" >nul 2>nul

curl -s -o nul -w "%%{http_code}" --max-time 3 http://127.0.0.1:7860/sdapi/v1/options > "%TEMP%\sc.txt" 2>nul
set /p SC=<"%TEMP%\sc.txt"
del "%TEMP%\sc.txt" >nul 2>nul

echo   Flask  http://127.0.0.1:5000/             HTTP %FC%
echo   SD API http://127.0.0.1:7860/sdapi/v1/... HTTP %SC%
echo.

REM 3) Diagnosis
echo [3/3] Diagnosis
echo ----------------------------------------
if "%FC%"=="200" if "%SC%"=="200" (
    echo [OK] Both services healthy. Browser should load fast.
    echo      If browser is still slow: hard refresh with Ctrl+Shift+R.
    goto :end
)
if "%FC%"=="0" echo [PROBLEM] Flask not responding. Check its console window.
if "%SC%"=="0" echo [PROBLEM] SD WebUI not responding. Launch A launcher.
if "%SC%"=="404" echo [PROBLEM] SD WebUI running but --api not enabled.
if "%SC%"=="000" echo [PROBLEM] Connection refused. SD WebUI may still be loading.

:end
echo.
echo Common fix: if 5000 has multiple LISTENINGs above, kill them:
echo   taskkill /F /IM python.exe /FI "WINDOWTITLE eq Flask*"
echo.
pause
