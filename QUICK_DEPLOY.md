# 快速部署指南（tango2086）

## 步骤 1：推送代码到 GitHub

双击运行 `push_commands.bat`，或者在命令行执行：

```bash
git remote add origin https://github.com/tango2086/atr-grid-trader-demo.git
git branch -M main
git push -u origin main
```

## 步骤 2：在 Render 创建服务

1. 访问 https://dashboard.render.com
2. GitHub 登录后，点击 **New +** → **Web Service**
3. 选择仓库：`tango2086/atr-grid-trader-demo`
4. 使用默认配置，点击 **Create Web Service**

## 步骤 3：等待部署

部署需要 2-3 分钟，你会在 Render 看到：

```
Your service is live at:
https://atr-grid-trader-demo.onrender.com
```

## 步骤 4：验证部署

运行验证脚本：

```bash
python verify.py
```

输入你的应用 URL 即可验证是否部署成功。

## 完成！

部署成功后，你的量化交易监控面板就可以通过公网访问了！