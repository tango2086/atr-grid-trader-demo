# test_web_api.py - 测试Web API
import requests
import json

def test_api():
    """测试Web API的今日收益计算"""
    base_url = "http://localhost:5000/api"

    try:
        print("测试Web API...")

        # 测试状态API
        response = requests.get(f"{base_url}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()

            if 'summary' in data:
                summary = data['summary']
                print(f"✅ 今日收益: {summary.get('day_profit', 0):.2f}元")
                print(f"✅ 总收益: {summary.get('total_profit', 0):.2f}元")
                print(f"✅ 浮盈: {summary.get('floating_pnl', 0):.2f}元")
                print(f"✅ 已实现盈亏: {summary.get('realized_pnl', 0):.2f}元")
            else:
                print("❌ API响应中缺少summary字段")
        else:
            print(f"❌ API请求失败: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Web服务器，请确保web_server.py正在运行")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_api()