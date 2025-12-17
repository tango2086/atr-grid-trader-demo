# test_orders_display.py - 测试建议订单显示
import requests
import json

def test_orders_display():
    """测试ETF监控页面是否显示建议订单"""
    base_url = "http://localhost:5000/api"

    try:
        print("测试建议订单显示...")

        # 获取状态数据
        response = requests.get(f"{base_url}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()

            print("\n=== ETF建议订单测试 ===")

            if 'etf_list' in data:
                for etf in data['etf_list']:
                    code = etf.get('code', 'Unknown')
                    name = etf.get('name', code)
                    orders = etf.get('orders', [])

                    print(f"\n[{code}] {name}")
                    print(f"  现价: ¥{etf.get('price', 0):.3f}")
                    print(f"  BIAS: {etf.get('bias', 0):.2f}%")
                    print(f"  状态: {etf.get('status', '未知')}")

                    if orders and len(orders) > 0:
                        print(f"  📋 建议订单 ({len(orders)}个):")
                        for i, order in enumerate(orders, 1):
                            direction = order.get('direction', 'N/A')
                            price = order.get('price', 0)
                            amount = order.get('amount', 0)
                            desc = order.get('desc', '')

                            icon = "🟢" if direction == 'BUY' else "🔴"
                            print(f"    {i}. {icon} {direction} ¥{price:.3f} × {amount}股 ({desc})")
                    else:
                        print("  📋 建议订单: 无")
            else:
                print("❌ API响应中没有ETF数据")
        else:
            print(f"❌ API请求失败: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Web服务器")
        print("请先启动Web服务器: python run.py -> 选择选项8")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_orders_display()