#!/usr/bin/env python3
"""
自动化部署脚本 - 部署到 Render
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_prerequisites():
    """检查先决条件"""
    print("[INFO] 检查先决条件...")

    # 检查必要文件
    required_files = [
        'render_deployment.py',
        'render_requirements.txt',
        'Procfile',
        'templates/index.html'
    ]

    for file in required_files:
        if not Path(file).exists():
            print(f"[ERROR] 缺少文件: {file}")
            return False
        print(f"[OK] 找到文件: {file}")

    return True

def initialize_git():
    """初始化 Git 仓库"""
    if Path('.git').exists():
        print("✅ Git 仓库已存在")
        return True

    print("📦 初始化 Git 仓库...")
    subprocess.run(['git', 'init'], check=True)

    # 创建 .gitignore
    gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database
*.db
*.sqlite
*.sqlite3

# Config
.env
config_local.py

# Logs
*.log
logs/

# Node modules
node_modules/

# OS
.DS_Store
Thumbs.db
"""

    with open('.gitignore', 'w', encoding='utf-8') as f:
        f.write(gitignore)

    print("✅ Git 仓库初始化完成")
    return True

def create_github_repo():
    """创建 GitHub 仓库指引"""
    print("\n📝 接下来请手动创建 GitHub 仓库：")
    print("1. 访问 https://github.com/new")
    print("2. 仓库名: atr-grid-trader-demo")
    print("3. 设为 Public（免费用户必须公开）")
    print("4. 不要添加 README、.gitignore 或 license")
    print("5. 点击 Create repository")
    print("\n创建后，GitHub 会显示类似这样的命令：")
    print("git remote add origin https://github.com/yourname/atr-grid-trader-demo.git")
    print("git branch -M main")
    print("git push -u origin main")

    input("\n按回车继续...")

def commit_and_push():
    """提交并推送代码"""
    print("\n🚀 准备提交并推送代码...")

    # 添加文件
    subprocess.run(['git', 'add', '.'], check=True)

    # 提交
    subprocess.run(['git', 'commit', '-m', 'Initial commit - ATR Grid Trader Demo'], check=True)

    print("\n📤 请执行以下命令推送到 GitHub：")
    print("（请替换 yourname 为你的 GitHub 用户名）")
    print("\ngit remote add origin https://github.com/yourname/atr-grid-trader-demo.git")
    print("git branch -M main")
    print("git push -u origin main")

    input("\n推送完成后按回车继续...")

def create_render_config():
    """创建 Render 配置说明"""
    render_config = {
        "services": [
            {
                "type": "web",
                "name": "atr-grid-trader",
                "env": "python",
                "buildCommand": "pip install -r render_requirements.txt",
                "startCommand": "gunicorn render_deployment:app --bind 0.0.0.0:$PORT --workers 1",
                "healthCheckPath": "/health",
                "envVars": [
                    {
                        "key": "PYTHON_VERSION",
                        "value": "3.9.0"
                    }
                ]
            }
        ]
    }

    with open('render.yaml', 'w', encoding='utf-8') as f:
        import yaml
        yaml.dump(render_config, f, default_flow_style=False)

    print("✅ 创建 render.yaml 配置文件")

def guide_render_deployment():
    """指导 Render 部署"""
    print("\n🎯 Render 部署步骤：")
    print("1. 访问 https://dashboard.render.com")
    print("2. 使用 GitHub 账号登录")
    print("3. 点击 'New +' → 'Web Service'")
    print("4. 选择刚创建的 GitHub 仓库")
    print("5. 配置如下：")
    print("   - Name: atr-grid-trader-demo")
    print("   - Environment: Python 3")
    print("   - Region: 选择最近的区域")
    print("   - Branch: main")
    print("   - Build Command: pip install -r render_requirements.txt")
    print("   - Start Command: gunicorn render_deployment:app --bind 0.0.0.0:$PORT")
    print("6. 点击 'Advanced Settings'")
    print("   - 添加健康检查路径: /health")
    print("7. 点击 'Create Web Service'")
    print("\n⏳ 部署需要 2-3 分钟...")

def create_deploy_verification():
    """创建部署验证脚本"""
    verify_script = """#!/usr/bin/env python3
\"\"\"
验证部署是否成功
\"\"\"

import requests
import time

def check_deployment(url):
    print(f"🔍 检查部署状态: {url}")

    # 检查主页
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("✅ 主页访问正常")
        else:
            print(f"❌ 主页返回状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法访问主页: {e}")
        return False

    # 检查 API
    try:
        api_url = f"{url}/api/status"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ API 状态正常")
            print(f"   - ETF 数量: {len(data.get('etf_list', []))}")
            print(f"   - 总资金: {data.get('summary', {}).get('total_capital', 0):,.0f}")
        else:
            print(f"❌ API 返回状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 访问失败: {e}")
        return False

    return True

if __name__ == "__main__":
    # 替换为你的实际 URL
    url = input("请输入你的应用 URL (例如: https://atr-grid-trader.onrender.com): ")

    if not url.startswith('http'):
        url = f"https://{url}"

    print("\\n⏳ 等待应用启动...")
    time.sleep(30)  # 等待应用启动

    if check_deployment(url):
        print("\\n🎉 部署验证成功！")
        print(f"📱 访问地址: {url}")
    else:
        print("\\n❌ 部署验证失败，请检查日志")
"""

    with open('verify_deployment.py', 'w', encoding='utf-8') as f:
        f.write(verify_script)

    print("✅ 创建部署验证脚本: verify_deployment.py")

def main():
    """主流程"""
    print("ATR Grid Trader - Render 自动部署助手")
    print("=" * 50)

    # 检查先决条件
    if not check_prerequisites():
        sys.exit(1)

    # 初始化 Git
    initialize_git()

    # 创建配置文件
    create_render_config()
    create_deploy_verification()

    # 指导创建 GitHub 仓库
    create_github_repo()

    # 指导推送代码
    commit_and_push()

    # 指导 Render 部署
    guide_render_deployment()

    print("\n✨ 部署准备完成！")
    print("\n📋 后续步骤：")
    print("1. 代码推送到 GitHub")
    print("2. 在 Render 创建 Web Service")
    print("3. 运行 python verify_deployment.py 验证")
    print("\n🔗 有用链接：")
    print("- GitHub: https://github.com")
    print("- Render: https://dashboard.render.com")
    print("- 应用文档: readthedoc")

if __name__ == "__main__":
    main()