#!/usr/bin/env python3
"""
验证部署是否成功
"""

import requests
import json

def test_api(url):
    """测试 API"""
    print(f"\n[INFO] 测试 API: {url}")

    try:
        # 测试状态 API
        response = requests.get(f"{url}/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("[OK] API 状态正常")
            print(f"  - ETF 数量: {len(data.get('etf_list', []))}")
            print(f"  - 数据源: {data.get('data_source', 'unknown')}")
            print(f"  - 总资金: {data.get('summary', {}).get('total_capital', 0):,.0f}")
            return True
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    """主函数"""
    print("ATR Grid Trader - 部署验证")
    print("=" * 40)

    url = input("\n请输入应用 URL: ").strip()
    if not url.startswith('http'):
        url = f"https://{url}"

    print(f"\n[INFO] 测试地址: {url}")

    # 测试主页
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            print("[OK] 主页访问成功")
        else:
            print(f"[ERROR] 主页访问失败: HTTP {r.status_code}")
            return
    except Exception as e:
        print(f"[ERROR] 无法访问主页: {e}")
        return

    # 测试 API
    if test_api(url):
        print("\n[SUCCESS] 部署验证成功！")
        print(f"\n访问地址: {url}")
    else:
        print("\n[FAILED] 部署验证失败")

if __name__ == "__main__":
    main()