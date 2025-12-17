#!/bin/bash

# 一键部署脚本 - 自动选择最佳方案
set -e

echo "🚀 BIAS-ATR-Grid-Trader 一键部署脚本"
echo "=================================="

# 检查系统
echo "📋 检查系统环境..."
OS=$(cat /etc/os-release | grep -w ID | cut -d'=' -f2 | tr -d '"')
echo "操作系统: $OS"

# 检查是否为Amazon Linux
if [ "$OS" != "amzn" ]; then
    echo "⚠️  此脚本专为Amazon Linux设计，其他系统可能需要调整"
fi

# 选择部署方案
echo ""
echo "请选择部署方案:"
echo "1) 传统Python部署 (推荐新手)"
echo "2) Docker部署 (推荐专业人士)"
echo "3) 仅安装环境，稍后手动部署"

read -p "请输入选择 (1-3): " -n 1 -r
echo

case $REPLY in
    1)
        echo "🐍 选择传统Python部署..."
        if [ -f "deploy_aws.sh" ]; then
            chmod +x deploy_aws.sh
            sudo ./deploy_aws.sh
        else
            echo "❌ 找不到 deploy_aws.sh 文件"
            exit 1
        fi
        ;;
    2)
        echo "🐳 选择Docker部署..."
        if [ -f "deploy_docker.sh" ]; then
            chmod +x deploy_docker.sh
            ./deploy_docker.sh
        else
            echo "❌ 找不到 deploy_docker.sh 文件"
            exit 1
        fi
        ;;
    3)
        echo "🛠️  仅安装环境..."
        sudo dnf update -y
        sudo dnf install -y python3 python3-pip git curl wget nginx docker
        echo "✅ 环境安装完成，请手动配置应用"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "🎉 部署脚本执行完成！"
echo ""
echo "📱 访问地址: http://13.204.65.251"
echo "📖 详细文档: AWS_DEPLOYMENT_GUIDE.md"
echo ""
echo "💡 提示: 如果遇到问题，请查看日志文件"