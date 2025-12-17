# AWS EC2 部署指南

## 🎯 服务器信息
- **实例ID**: i-0a67d84c04f269f3f
- **公有IP**: 13.204.65.251
- **公有DNS**: ec2-13-204-65-251.ap-south-1.compute.amazonaws.com
- **系统**: Amazon Linux 2023
- **实例类型**: t3.micro

## 🚀 部署方案选择

### 方案1：传统Python部署（推荐新手）
**优点**: 简单直接、资源占用少、易调试
**缺点**: 环境依赖系统Python版本

### 方案2：Docker容器化部署（推荐专业人士）
**优点**: 环境隔离、易扩展、可移植
**缺点**: 需要额外学习Docker

---

## 📋 方案1：传统Python部署步骤

### 1. 连接到服务器
```bash
# 使用您的密钥文件连接
ssh -i "atr-grid-trader.pem" ec2-user@13.204.65.251
```

### 2. 上传代码文件
```bash
# 在本地终端执行
scp -i "atr-grid-trader.pem" -r ./* ec2-user@13.204.65.251:/home/ec2-user/
```

### 3. 运行部署脚本
```bash
# 在服务器上执行
sudo chmod +x deploy_aws.sh
sudo ./deploy_aws.sh
```

### 4. 手动部署（如果脚本失败）
```bash
# 1. 更新系统
sudo dnf update -y

# 2. 安装依赖
sudo dnf install -y python3 python3-pip git nginx

# 3. 创建应用目录
sudo mkdir -p /opt/atr-grid-trader
sudo cp -r * /opt/atr-grid-trader/
sudo chown -R ec2-user:ec2-user /opt/atr-grid-trader

# 4. 安装Python依赖
cd /opt/atr-grid-trader
pip3 install --user -r requirements.txt
pip3 install --user gunicorn

# 5. 创建systemd服务
sudo nano /etc/systemd/system/atr-grid-trader.service
```

### 5. 验证部署
```bash
# 访问您的应用
curl http://13.204.65.251/health

# 或在浏览器中访问
http://13.204.65.251
```

---

## 🐳 方案2：Docker部署步骤

### 1. 连接服务器
```bash
ssh -i "atr-grid-trader.pem" ec2-user@13.204.65.251
```

### 2. 安装Docker
```bash
# 更新系统
sudo dnf update -y

# 安装Docker
sudo dnf install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 重新登录以应用用户组更改
exit
ssh -i "atr-grid-trader.pem" ec2-user@13.204.65.251
```

### 3. 上传并部署
```bash
# 上传代码
scp -i "atr-grid-trader.pem" -r ./* ec2-user@13.204.65.251:/home/ec2-user/

# 在服务器上部署
chmod +x deploy_docker.sh
./deploy_docker.sh
```

---

## 🔧 重要配置

### 安全组设置（在AWS控制台）
确保以下端口开放：
- **HTTP (80)**: Web访问
- **HTTPS (443)**: SSL访问（可选）
- **SSH (22)**: 远程连接
- **自定义 (5000)**: 应用端口（可选）

### 防火墙设置
```bash
# 查看防火墙状态
sudo systemctl status firewalld

# 如果启用，添加端口
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## 📊 服务管理

### 检查服务状态
```bash
# 传统部署
sudo systemctl status atr-grid-trader
sudo systemctl status nginx

# Docker部署
docker-compose ps
```

### 查看日志
```bash
# 传统部署
sudo journalctl -u atr-grid-trader -f
sudo tail -f /var/log/nginx/access.log

# Docker部署
docker-compose logs -f
```

### 重启服务
```bash
# 传统部署
sudo systemctl restart atr-grid-trader

# Docker部署
docker-compose restart
```

---

## 🌐 域名配置（可选）

### 使用Cloudflare（免费）
1. 注册Cloudflare账号
2. 将域名指向 13.204.65.251
3. 启用免费SSL证书

### 配置域名后的Nginx设置
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        # ... 其他配置
    }
}
```

---

## 🔍 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   sudo lsof -i :5000
   sudo kill -9 <PID>
   ```

2. **Python依赖问题**
   ```bash
   pip3 install --upgrade pip
   pip3 install -r requirements.txt --force-reinstall
   ```

3. **权限问题**
   ```bash
   sudo chown -R ec2-user:ec2-user /opt/atr-grid-trader
   ```

4. **Nginx配置错误**
   ```bash
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### 性能监控
```bash
# 系统资源
htop
df -h
free -h

# 应用监控
curl http://localhost:5000/health
```

---

## 📱 访问地址

部署成功后，您可以通过以下地址访问应用：

- **主地址**: http://13.204.65.251
- **备用地址**: http://ec2-13-204-65-251.ap-south-1.compute.amazonaws.com

---

## 🛡️ 安全建议

1. **定期更新系统**
   ```bash
   sudo dnf update -y
   ```

2. **配置防火墙**
   ```bash
   sudo firewall-cmd --permanent --add-service=ssh
   sudo firewall-cmd --reload
   ```

3. **使用强密码/密钥**
   - 确保SSH密钥安全
   - 定期更换密码

4. **备份数据**
   ```bash
   # 备份应用数据
   sudo tar -czf atr-backup-$(date +%Y%m%d).tar.gz /opt/atr-grid-trader
   ```

---

## 🎉 部署完成

如果一切顺利，您现在应该可以看到BIAS-ATR网格交易系统的Web界面了！

**访问地址**: http://13.204.65.251

**技术支持**:
- 查看应用日志排查问题
- 检查AWS安全组设置
- 确认所有服务正在运行