@echo off
chcp 65001 >nul 2>&1
title 九章量化局 v2.0 - Flask看板

echo ========================================
echo   九章量化局 v2.0 · Flask服务器
echo   SQLite + 多线程 + 日志系统
echo ========================================
echo.

:: 关闭旧进程
taskkill /F /IM python.exe >nul 2>&1
timeout /t 1 /nobreak >nul

:: 启动Flask服务器
cd /d "%~dp0dashboard"
start /b "" "C:\Users\let2free\.workbuddy\binaries\python\versions\3.13.12\python.exe" app.py

:: 等待启动
echo 等待Flask服务器启动...
timeout /t 3 /nobreak >nul

:: 打开浏览器
start http://localhost:7860

echo.
echo ✅ 九章量化局 v2.0 已启动！
echo   主页: http://localhost:7860
echo   日志: dashboard/logs/
echo   数据库: dashboard/jiuzhang.db
echo.
pause
