#!/bin/bash
# 教师信息管理系统 - Mac/Linux 启动脚本

echo "========================================="
echo "   🎓 教师信息管理系统"
echo "========================================="
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 检测 Python
PYTHON=""
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "❌ 未找到 Python，请先安装 Python 3.8+"
    echo "   推荐使用 Homebrew 安装: brew install python3"
    exit 1
fi

echo "📌 使用 Python: $($PYTHON --version)"

# 校验虚拟环境是否有效（目录搬迁后旧 venv 常会失效）
RECREATE_VENV=0
EXPECTED_VENV_PATH="$(pwd)/venv"

if [ ! -d "venv" ] || [ ! -x "venv/bin/python" ]; then
    RECREATE_VENV=1
elif ! grep -q "$EXPECTED_VENV_PATH" "venv/bin/activate" 2>/dev/null; then
    RECREATE_VENV=1
fi

# 创建或重建虚拟环境
if [ "$RECREATE_VENV" -eq 1 ]; then
    echo ""
    echo "📦 创建/重建虚拟环境..."
    rm -rf venv
    $PYTHON -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ 虚拟环境创建失败"
        echo "   请尝试: brew install python3 或使用 conda"
        exit 1
    fi
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo ""
echo "📦 检查并安装依赖..."
python -m pip install --upgrade pip -q 2>&1 || true
python -m pip install -r backend/requirements.txt -q 2>&1

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    echo "   可能原因：网络不可用，或 PyPI 源不可访问"
    echo "   建议重试："
    echo "   1) python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple"
    echo "   2) ./run.sh"
    exit 1
fi

# 检查端口占用
if lsof -iTCP:8000 -sTCP:LISTEN -n -P >/dev/null 2>&1; then
    echo ""
    echo "⚠️ 端口 8000 已被占用，当前监听进程："
    lsof -iTCP:8000 -sTCP:LISTEN -n -P
    echo ""
    echo "请先停止占用进程，或修改启动端口。"
    exit 1
fi

echo ""
echo "✅ 依赖安装完成"
echo ""
echo "🚀 启动服务..."
echo "   访问地址: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo "   按 Ctrl+C 停止服务"
echo ""

# 启动服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
