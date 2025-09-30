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
echo 🎯 只停止端口5001的服务，不影响其他Python程序
echo.

REM 查找并停止占用5001端口的进程（Flask后端）
echo [1/2] 停止后端服务 (端口5001)...
set "found_backend=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5001.*LISTENING 2^>nul') do (
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
    echo ℹ️  未找到端口5001上的服务
)

echo.
echo ℹ️  现在使用一体化服务，无需停止单独的前端服务

REM 检查是否还有服务在运行
echo.
echo 检查服务状态...
netstat -ano | findstr :5001.*LISTENING >nul 2>&1
if %errorlevel% equ 0 (
    echo ⚠️  端口5001仍被占用
) else (
    echo ✅ 端口5001已释放
)

echo.
echo ========================================
echo 🎯 精确停止完成！
echo 👍 股票查看器一体化服务已停止
echo ========================================
echo.
pause
