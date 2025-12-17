#!/bin/bash

# AWS EC2 部署脚本
# 适用于 Amazon Linux 2023

set -e

echo "🚀 开始部署 BIAS-ATR-Grid-Trader 到 AWS EC2"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 更新系统
echo "📦 更新系统包..."
dnf update -y

# 安装必要软件
echo "📦 安装系统依赖..."
dnf install -y python3 python3-pip git curl wget nginx

# 安装Docker (可选)
read -p "是否安装Docker? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🐳 安装Docker..."
    dnf install -y docker
    systemctl start docker
    systemctl enable docker
    usermod -a -G docker ec2-user

    # 安装Docker Compose
    curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

    echo "✅ Docker 安装完成"
fi

# 创建应用目录
APP_DIR="/opt/atr-grid-trader"
echo "📁 创建应用目录: $APP_DIR"
mkdir -p $APP_DIR
cd $APP_DIR

# 克隆代码（这里需要替换为您的Git仓库）
read -p "请输入您的Git仓库URL (或按回车跳过，使用本地上传): " GIT_URL
if [ ! -z "$GIT_URL" ]; then
    echo "📥 克隆代码..."
    git clone $GIT_URL .
else
    echo "⚠️  请手动上传代码文件到 $APP_DIR"
fi

# 设置文件权限
chown -R ec2-user:ec2-user $APP_DIR
chmod +x $APP_DIR/*.py

# 安装Python依赖
echo "🐍 安装Python依赖..."
cd $APP_DIR
pip3 install --upgrade pip
pip3 install -r requirements.txt
pip3 install gunicorn

# 创建systemd服务文件
echo "⚙️ 创建系统服务..."
cat > /etc/systemd/system/atr-grid-trader.service << EOF
[Unit]
Description=ATR Grid Trader
After=network.target

[Service]
Type=exec
User=ec2-user
Group=ec2-user
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
Environment=PORT=5000
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 render_deployment:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 配置Nginx
echo "🌐 配置Nginx..."
cat > /etc/nginx/conf.d/atr-grid-trader.conf << EOF
server {
    listen 80;
    server_name 13.204.65.251 ec2-13-204-65-251.ap-south-1.compute.amazonaws.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        access_log off;
    }
}
EOF

# 测试Nginx配置
nginx -t

# 启动服务
echo "🚀 启动服务..."
systemctl daemon-reload
systemctl enable atr-grid-trader
systemctl start atr-grid-trader
systemctl restart nginx

# 配置防火墙（如果启用）
echo "🔥 配置防火墙..."
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --permanent --add-port=5000/tcp
    firewall-cmd --reload
fi

# 显示状态
echo "📊 检查服务状态..."
systemctl status atr-grid-trader --no-pager
systemctl status nginx --no-pager

echo ""
echo "✅ 部署完成！"
echo ""
echo "📱 访问地址："
echo "   http://13.204.65.251"
echo "   http://ec2-13-204-65-251.ap-south-1.compute.amazonaws.com"
echo ""
echo "🔧 管理命令："
echo "   查看日志: sudo journalctl -u atr-grid-trader -f"
echo "   重启服务: sudo systemctl restart atr-grid-trader"
echo "   查看状态: sudo systemctl status atr-grid-trader"
echo ""
echo "📁 应用目录: $APP_DIR"
echo "📋 配置文件: /etc/nginx/conf.d/atr-grid-trader.conf"