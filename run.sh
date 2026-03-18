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

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 创建虚拟环境..."
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
pip install -r backend/requirements.txt -q 2>&1

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败，请检查网络连接"
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
