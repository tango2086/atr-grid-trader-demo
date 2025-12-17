#!/bin/bash

# Docker部署脚本 - AWS EC2
set -e

echo "🐳 Docker部署 BIAS-ATR-Grid-Trader"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先运行 install_docker.sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先运行 install_docker.sh"
    exit 1
fi

# 创建应用目录
APP_DIR="/opt/atr-grid-trader"
echo "📁 创建应用目录: $APP_DIR"
sudo mkdir -p $APP_DIR
sudo chown ec2-user:ec2-user $APP_DIR

cd $APP_DIR

# 复制文件（这里假设文件已经上传）
echo "📋 准备应用文件..."

# 创建必要的目录
mkdir -p logs data ssl

# 构建并启动服务
echo "🏗️ 构建Docker镜像..."
docker-compose build

echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 测试健康检查
echo "🏥 测试健康检查..."
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ 应用健康检查通过"
else
    echo "❌ 应用健康检查失败"
fi

echo ""
echo "✅ Docker部署完成！"
echo ""
echo "📱 访问地址："
echo "   http://13.204.65.251"
echo ""
echo "🔧 管理命令："
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
echo "   查看状态: docker-compose ps"
echo ""
echo "📁 应用目录: $APP_DIR"