#!/bin/bash
# setup_rag.sh — 一键安装依赖并建立知识库索引

set -e

echo "================================================"
echo "  DramaRAG 环境初始化"
echo "================================================"
echo ""

# 切换到项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 检查 .env
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件，请先复制 .env.example 并填写 DASHSCOPE_API_KEY"
    exit 1
fi

echo "✅ .env 文件已找到"
echo ""

# 安装 Python 依赖
echo "📦 安装 Python 依赖..."
pip3 install --quiet openai chromadb python-dotenv
echo "✅ 依赖安装完成"
echo ""

# 建立索引
echo "📚 开始建立知识库索引..."
echo "   (麦基故事 + 救猫咪 + 基本剧作法，约需 1-3 分钟)"
echo ""
python scripts/drama_rag.py --ingest

echo ""
echo "================================================"
echo "✅ 初始化完成！验证检索效果："
echo ""
echo "  python scripts/drama_rag.py --query '人物冲突设计'"
echo "  python scripts/drama_rag.py --status"
echo "================================================"
