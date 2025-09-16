@echo off
setlocal enabledelayedexpansion
chcp 65001
title 停止股票查看器服务
echo.
echo ========================================
echo   📈 股票信息查看器 - 精确停止脚本
echo ========================================
echo.

echo 正在精确停止股票查看器相关服务...
echo 🎯 只停止端口5000和8080的服务，不影响其他Python程序
echo.

REM 查找并停止占用5000端口的进程（Flask后端）
echo [1/2] 停止后端服务 (端口5000)...
set "found_backend=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000.*LISTENING 2^>nul') do (
    echo 发现后端进程 PID: %%a
    taskkill /pid %%a /f >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ 后端服务已停止 (PID: %%a)
        set "found_backend=1"
    ) else (
        echo ❌ 停止后端服务失败 (PID: %%a)
    )
)
if !found_backend! equ 0 (
    echo ℹ️  未找到端口5000上的服务
)

REM 查找并停止占用8080端口的进程（HTTP服务器）
echo.
echo [2/2] 停止前端服务 (端口8080)...
set "found_frontend=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8080.*LISTENING 2^>nul') do (
    echo 发现前端进程 PID: %%a
    taskkill /pid %%a /f >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ 前端服务已停止 (PID: %%a)
        set "found_frontend=1"
    ) else (
        echo ❌ 停止前端服务失败 (PID: %%a)
    )
)
if !found_frontend! equ 0 (
    echo ℹ️  未找到端口8080上的服务
)

REM 检查是否还有服务在运行
echo.
echo 检查服务状态...
netstat -ano | findstr :5000.*LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo ⚠️  端口5000仍被占用
) else (
    echo ✅ 端口5000已释放
)

netstat -ano | findstr :8080.*LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo ⚠️  端口8080仍被占用
) else (
    echo ✅ 端口8080已释放
)

echo.
echo ========================================
echo 🎯 精确停止完成！
echo 👍 只停止了股票查看器服务，其他Python程序未受影响
echo ========================================
echo.
pause
