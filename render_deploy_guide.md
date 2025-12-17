# Render 部署指南

## 部署步骤

### 1. 准备代码

1. 将项目推送到 GitHub 仓库
2. 确保包含以下文件：
   - `render_deployment.py` - 简化版 Web 服务
   - `render_requirements.txt` - 依赖列表
   - `Procfile` - Render 配置文件
   - `templates/index.html` - 前端模板

### 2. 登录 Render

1. 访问 [render.com](https://render.com)
2. 使用 GitHub 账号登录
3. 授权 Render 访问你的仓库

### 3. 创建 Web Service

1. 点击 "New" -> "Web Service"
2. 选择你的 GitHub 仓库
3. 配置服务：
   - **Name**: your-app-name
   - **Environment**: Python 3
   - **Region**: 选择最近的区域
   - **Branch**: main/master
   - **Root Directory**: 留空
   - **Runtime**: Docker 或 Python
   - **Build Command**: `pip install -r render_requirements.txt`
   - **Start Command**: `gunicorn render_deployment:app --bind 0.0.0.0:$PORT`

### 4. 环境变量（可选）

在 Render 控制台添加环境变量：
- `PYTHON_VERSION`: 3.9.0
- `FLASK_ENV`: production

### 5. 部署限制说明

**免费版限制：**
- ❌ 无法持久化存储数据（重启后数据丢失）
- ❌ 15分钟无访问会睡眠
- ❌ 不支持实时交易功能
- ❌ 无法使用 akshare 等需要频繁调用的API
- ✅ 可以展示静态和模拟数据
- ✅ 支持 Web UI 访问
- ✅ 支持基础交互功能

**建议用途：**
- 作为项目演示展示
- 不需要实时数据的监控面板
- 学习和测试用途

### 6. 升级方案

如需完整功能，考虑：
1. **Render Starter 计划** ($7/月)
   - 持久化磁盘
   - 不睡眠
   - 更多资源

2. **其他云服务**
   - Railway
   - Vercel（前端）
   - Heroku（已收费）
   - 阿里云/腾讯云国内服务

3. **自建服务器**
   - 轻量应用服务器
   - 树莓派
   - 家用 NAS

### 7. 替代方案

如果只是想远程访问，可以：
1. 使用 **ngrok** 内网穿透
2. 使用 **frp** 反向代理
3. 搭建 **VPN** 服务
4. 使用 **GitHub Pages** + GitHub Actions（仅前端）

### 8. 注意事项

- 演示版本使用模拟数据，不代表真实市场
- 交易功能已禁用，仅展示界面
- 定期访问防止实例睡眠（可设置 Cron Job）
- 建议添加访问密码保护