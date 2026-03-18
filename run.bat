@echo off
chcp 65001 >nul
REM 教师信息管理系统 - Windows 启动脚本

echo =========================================
echo    教师信息管理系统
echo =========================================
echo.

cd /d "%~dp0"

REM 检测 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo 使用 Python:
python --version

REM 创建虚拟环境（如果不存在）
if not exist "venv" (
    echo.
    echo 创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo 虚拟环境创建失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

echo.
echo 检查并安装依赖...
pip install -r backend\requirements.txt -q

if %errorlevel% neq 0 (
    echo 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)

echo.
echo 依赖安装完成
echo.
echo 启动服务...
echo    访问地址: http://localhost:8000
echo    API 文档: http://localhost:8000/docs
echo    按 Ctrl+C 停止服务
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause
