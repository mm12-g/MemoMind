# ============================================================
# MemoMind 一键部署脚本 (Linux)
# 使用: bash deploy/deploy.sh
# ============================================================
#!/usr/bin/env bash
set -e

echo "========================================"
echo "  MemoMind 生产部署"
echo "========================================"

cd "$(dirname "$0")"

# 1. 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose v2 未安装"
    exit 1
fi
echo "✅ Docker 环境检查通过"

# 2. 检查 .env
if [ ! -f .env ]; then
    if [ -f .env.prod ]; then
        cp .env.prod .env
        echo "⚠️  已从 .env.prod 复制为 .env，请修改 .env 填入真实配置"
        echo "   然后重新运行此脚本"
        exit 1
    else
        echo "❌ 未找到 .env 文件"
        exit 1
    fi
fi
echo "✅ .env 配置文件就绪"

# 3. 生成 JWT Secret（如果是占位符）
source .env
if [[ "$JWT_SECRET_KEY" == *"REPLACE"* ]] || [[ "$JWT_SECRET_KEY" == *"CHANGE"* ]]; then
    NEW_SECRET=$(openssl rand -hex 32)
    sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$NEW_SECRET|" .env
    echo "🔑 已自动生成 JWT_SECRET_KEY"
fi

# 4. 构建并启动
echo "📦 构建并启动服务..."
docker compose up -d --build

# 5. 等待后端就绪
echo "⏳ 等待后端启动..."
for i in $(seq 1 30); do
    if docker compose logs backend --tail 5 2>/dev/null | grep -q "Uvicorn running\|Application startup complete"; then
        echo "✅ 后端已启动"
        break
    fi
    sleep 2
done

# 6. 数据库迁移
echo "🗄️  执行数据库迁移..."
docker compose exec backend alembic upgrade head
echo "✅ 数据库迁移完成"

# 7. 显示状态
echo ""
echo "========================================"
echo "  🎉 部署完成！"
echo "========================================"
docker compose ps
echo ""
echo "🌐 访问地址: http://${FRONTEND_PORT:-80} (或服务器IP)"
echo ""
echo "常用命令:"
echo "  查看日志: docker compose logs -f"
echo "  停止服务: docker compose down"
echo "  重启后端: docker compose restart backend"
echo "  重新部署: docker compose up -d --build"
echo "  数据库迁移: docker compose exec backend alembic upgrade head"
