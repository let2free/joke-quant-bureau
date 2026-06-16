@echo off
chcp 65001 > nul
echo ============================================================
echo   九章量化局 - 实时看板启动脚本
echo ============================================================
echo.

cd /d %~dp0

echo [1/3] 检查Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或不在PATH中
    pause
    exit /b 1
)
python --version

echo.
echo [2/3] 安装依赖...
pip install -r requirements.txt -q

echo.
echo [3/3] 启动看板服务器...
echo.
echo ✅ 启动成功！
echo.
echo 访问地址：
echo   主看板：  <ADDRESS_REMOVED>
echo   协同中心：<ADDRESS_REMOVED>
echo.
echo 按 Ctrl+C 停止服务器
echo ============================================================
echo.

python dashboard_server.py
