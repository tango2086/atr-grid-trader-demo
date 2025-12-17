#!/usr/bin/env python3
"""
简化版部署脚本 - 部署到 Render
"""

import os
import subprocess
from pathlib import Path

def check_files():
    """检查必要文件"""
    print("[INFO] 检查部署文件...")

    required = ['render_deployment.py', 'render_requirements.txt', 'Procfile', 'templates/index.html']
    missing = []

    for f in required:
        if not Path(f).exists():
            missing.append(f)
        else:
            print(f"[OK] {f}")

    if missing:
        print(f"[ERROR] 缺少文件: {', '.join(missing)}")
        return False
    return True

def init_git():
    """初始化 Git"""
    print("\n[INFO] 初始化 Git 仓库...")

    if not Path('.git').exists():
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        print("[OK] Git 仓库初始化完成")
    else:
        print("[OK] Git 仓库已存在")

    # 创建 .gitignore
    gitignore = """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
*.db
*.sqlite
*.sqlite3
.env
venv/
ENV/
.vscode/
.idea/
.DS_Store
"""

    if not Path('.gitignore').exists():
        with open('.gitignore', 'w') as f:
            f.write(gitignore)
        print("[OK] 创建 .gitignore")

def commit_files():
    """提交文件"""
    print("\n[INFO] 提交文件...")

    subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Add ATR Grid Trader demo for Render'], check=True, capture_output=True)
    print("[OK] 文件已提交")

def main():
    """主流程"""
    print("=" * 50)
    print("ATR Grid Trader - Render 部署助手")
    print("=" * 50)

    # 检查文件
    if not check_files():
        return

    # 初始化 Git
    init_git()

    # 提交文件
    commit_files()

    # 打印后续步骤
    print("\n" + "=" * 50)
    print("后续步骤：")
    print("1. 访问 https://github.com/new 创建新仓库")
    print("2. 仓库名: atr-grid-trader-demo (设为 Public)")
    print("3. 执行以下命令（替换 yourname）：")
    print("")
    print("   git remote add origin https://github.com/yourname/atr-grid-trader-demo.git")
    print("   git branch -M main")
    print("   git push -u origin main")
    print("")
    print("4. 访问 https://dashboard.render.com")
    print("5. 连接 GitHub，选择刚创建的仓库")
    print("6. 使用默认配置，点击 Deploy")
    print("")
    print("部署完成后，运行 verify.py 验证")
    print("=" * 50)

if __name__ == "__main__":
    main()