@echo off
chcp 65001 >nul 2>&1
title 九章量化局 - 看板服务器

echo ========================================
echo   九章量化局 · 看板服务器启动中...
echo ========================================
echo.

:: 关闭旧进程
taskkill /F /IM python.exe >nul 2>&1
timeout /t 1 /nobreak >nul

:: 启动服务器
cd /d "%~dp0dashboard"
start /b "" python dashboard_server.py

:: 等待服务器启动
echo 等待服务器启动...
timeout /t 3 /nobreak >nul

:: 自动打开浏览器
start http://localhost:7860

echo.
echo ✅ 服务器已启动！
echo.
echo   主页地址: http://localhost:7860
echo.
echo   关闭此窗口不影响服务器运行
echo   如需停止服务器，运行: taskkill /F /IM python.exe
echo.
pause
