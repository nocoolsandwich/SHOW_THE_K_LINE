@echo off
chcp 65001
title 股票信息查看器 - 一键启动
echo.
echo ========================================
echo   📈 股票信息查看器 - 一键启动脚本
echo ========================================
echo.

REM 检查Python环境
echo [1/5] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python未安装或未配置到环境变量！
    echo 请先安装Python 3.7+并添加到PATH环境变量
    pause
    exit /b 1
)
echo ✅ Python环境检查通过

REM 检查依赖
echo.
echo [2/5] 检查Python依赖...
if not exist "requirements.txt" (
    echo ❌ 找不到requirements.txt文件！
    pause
    exit /b 1
)

REM 安装依赖（如果需要）
echo 正在检查依赖包...
pip show flask >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败！
        pause
        exit /b 1
    )
)
echo ✅ 依赖检查完成

REM 检查后端文件
echo.
echo [3/5] 检查项目文件...
if not exist "backend.py" (
    echo ❌ 找不到backend.py文件！
    pause
    exit /b 1
)
if not exist "index.html" (
    echo ❌ 找不到index.html文件！
    pause
    exit /b 1
)
echo ✅ 项目文件检查通过

REM 启动后端服务
echo.
echo [4/5] 启动后端服务...
echo 正在启动Flask后端服务 (端口5000)...
start "后端服务" cmd /k "python backend.py"

REM 等待后端启动
echo 等待后端服务启动...
timeout /t 3 /nobreak >nul

REM 启动前端服务
echo.
echo [5/5] 启动前端服务...
echo 正在启动前端HTTP服务 (端口8080)...
start "前端服务" cmd /k "python -m http.server 8080"

REM 等待前端启动
echo 等待前端服务启动...
timeout /t 2 /nobreak >nul

REM 打开浏览器
echo.
echo 🚀 启动完成！正在打开浏览器...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8080

echo.
echo ========================================
echo ✅ 服务启动成功！
echo.
echo 📊 后端API服务: http://127.0.0.1:5000
echo 🌐 前端页面:   http://127.0.0.1:8080
echo.
echo 使用说明:
echo - 上传PDF文件或粘贴文本来识别股票
echo - 鼠标悬停查看迷你K线图
echo - 点击股票名称查看详细信息
echo.
echo ⚠️  关闭此窗口会停止股票查看器服务
echo ⚠️  如需单独停止服务，请运行 stop.bat
echo 💡 新功能: 精确停止，不影响其他Python程序
echo ========================================
echo.

REM 保持主窗口打开
echo 按任意键退出并停止股票查看器服务...
pause >nul

REM 精确清理股票查看器进程
echo.
echo 正在停止股票查看器服务...
echo 调用精确停止脚本...
call scripts\stop_simple.bat
echo 股票查看器服务已停止
timeout /t 1 /nobreak >nul
