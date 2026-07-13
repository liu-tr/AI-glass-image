@echo off
chcp 65001 >nul
setlocal

set "SD_LAUNCHER=F:\sd-webui-aki-v4.10\A绘世启动器.exe"
set "SD_PORT=7860"

echo ============================================================
echo   SD WebUI 环境自检
echo ============================================================
echo.

REM 1. 整合包路径
echo [1/3] 检查整合包启动器: %SD_LAUNCHER%
if exist "%SD_LAUNCHER%" (
    echo       [OK] 文件存在
) else (
    echo       [FAIL] 文件不存在
    echo             解决：编辑 start_all.bat 顶部 SD_LAUNCHER 为正确路径
)
echo.

REM 2. 端口占用
echo [2/3] 检查端口 %SD_PORT% 占用情况
netstat -ano | findstr ":%SD_PORT% " | findstr "LISTENING" >nul
if !errorlevel! equ 0 (
    echo       [WARN] 端口已被占用
    echo             占用详情：
    netstat -ano | findstr ":%SD_PORT% " | findstr "LISTENING"
    echo             结束占用进程：taskkill /F /PID ^<上面最后一列的数字^>
) else (
    echo       [OK] 端口空闲
)
echo.

REM 3. API 探活（如果端口已被占）
echo [3/3] 尝试访问 http://127.0.0.1:%SD_PORT%/sdapi/v1/options
curl -s -o nul -w "       HTTP 代码: %%{http_code}" --max-time 3 http://127.0.0.1:%SD_PORT%/sdapi/v1/options
echo.
echo.
echo 结论：
echo   200 = WebUI 已在运行且 API 已开启，直接跑 start_all.bat 即可
echo   404 = WebUI 已在运行但没加 --api，去 webui-user.bat 加参数
echo   000 = WebUI 未运行，先双击 A绘世启动器.exe
echo.
pause
