# smart_main.py
import pandas as pd
import datetime
import os
import sys
from typing import Dict, List
import config
from strategy import GridStrategy, TradePlan

# 尝试导入 QMT 数据源 (xtquant)
try:
    if hasattr(config, 'QMT_PATH') and config.QMT_PATH:
        sys.path.insert(0, config.QMT_PATH)
    from xtquant import xtdata
    xtdata.connect()
    print("✅ QMT数据源连接成功")
except Exception as e:
    xtdata = None
    print(f"⚠️  QMT未连接，将使用模拟数据: {e}")

def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """打印横幅"""
    print("=" * 70)
    print("🤖 BIAS-ATR-Grid-Trader 智能交易系统 v2.0")
    print("   让网格交易更智能、更简单")
    print("=" * 70)
    print()

def get_user_choice() -> str:
    """获取用户选择"""
    print("📋 请选择操作：")
    print("1. 🚀 一键生成今日交易计划")
    print("2. ⚙️  智能配置向导")
    print("3. 📊 查看历史报告")
    print("4. 🔍 单独分析ETF")
    print("5. ⚙️  参数设置")
    print("6. 📖 使用帮助")
    print("0. 🚪 退出系统")
    print()

    while True:
        choice = input("请输入选择(0-6): ").strip()
        if choice in ['0', '1', '2', '3', '4', '5', '6']:
            return choice
        print("❌ 请输入有效选项(0-6)")

def smart_generate_daily_plan():
    """智能生成当日交易计划"""
    clear_screen()
    print_banner()
    print("🚀 正在智能生成今日交易计划...")
    print()

    # 检查是否有智能配置
    if os.path.exists('smart_config.py'):
        try:
            import smart_config
            etf_list = [etf['code'] for etf in smart_config.SMART_ETF_LIST]
            print("✅ 使用智能配置")
        except:
            etf_list = config.ETF_CODE_LIST if hasattr(config, 'ETF_CODE_LIST') else config.ETF_LIST
            print("⚠️  使用默认配置")
    else:
        etf_list = config.ETF_CODE_LIST if hasattr(config, 'ETF_CODE_LIST') else config.ETF_LIST
        print("💡 提示：运行智能配置向导可获得个性化建议")

    strategy = GridStrategy()
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    report_file = f"smart_trade_plan_{today_str}.md"

    # 进度条显示
    total_etfs = len(etf_list)
    plans = []

    for i, code in enumerate(etf_list, 1):
        print(f"📊 分析中 {i}/{total_etfs}: {code}", end=" ... ")

        try:
            # 使用真实持仓（如有配置）
            real_holdings = getattr(config, 'REAL_HOLDINGS', {})
            holdings = real_holdings.get(code, {
                'volume': 10000,
                'available': 10000,
                'avg_cost': 0
            })

            # 获取数据
            df = get_data(code)
            if df is not None and not df.empty:
                if holdings.get('avg_cost', 0) == 0:
                    holdings['avg_cost'] = df['close'].iloc[-1] * 0.95

            plan = strategy.analyze(code, df, holdings)
            plans.append(plan)

            status_emoji = {"DEEP_DIP": "🟢", "GOLD_ZONE": "🟡", "OSCILLATION": "🔵",
                           "REDUCE_ZONE": "🟠", "ESCAPE_ZONE": "🔴"}.get(plan.market_status.split()[0], "⚪")
            print(f"{status_emoji} {plan.market_status}")

        except Exception as e:
            print(f"❌ 失败: {str(e)[:50]}")

    # 生成智能报告
    generate_smart_report(plans, report_file)

    # 显示摘要
    print("\n" + "="*50)
    print("📈 今日市场概览:")

    status_count = {}
    total_buy_orders = 0
    total_sell_orders = 0

    for plan in plans:
        status = plan.market_status.split()[0]
        status_count[status] = status_count.get(status, 0) + 1

        for order in plan.suggested_orders:
            if order.direction == 'BUY':
                total_buy_orders += 1
            else:
                total_sell_orders += 1

    for status, count in status_count.items():
        emoji = {"DEEP_DIP": "🟢", "GOLD_ZONE": "🟡", "OSCILLATION": "🔵",
                "REDUCE_ZONE": "🟠", "ESCAPE_ZONE": "🔴"}.get(status, "⚪")
        print(f"  {emoji} {status}: {count}只")

    print(f"\n📋 今日建议:")
    print(f"  🛒 买入信号: {total_buy_orders}个")
    print(f"  💰 卖出信号: {total_sell_orders}个")

    print(f"\n📄 详细报告已保存到: {report_file}")

    input("\n按回车键继续...")

def get_data(code: str) -> pd.DataFrame:
    """获取ETF数据 (QMT数据源)"""
    # 1. 尝试 QMT
    if xtdata:
        try:
            # 转换代码格式: sh510050 -> 510050.SH
            symbol = code[2:] + '.' + code[:2].upper()
            
            # 下载并获取历史数据
            xtdata.download_history_data(symbol, period='1d', incrementally=True)
            
            data = xtdata.get_market_data(
                field_list=['open', 'high', 'low', 'close', 'volume'],
                stock_list=[symbol],
                period='1d',
                count=200
            )
            
            if data and 'close' in data and len(data['close']) > 0:
                df = pd.DataFrame({
                    'open': data['open'][symbol],
                    'high': data['high'][symbol],
                    'low': data['low'][symbol],
                    'close': data['close'][symbol],
                    'volume': data['volume'][symbol]
                })
                df.index = pd.to_datetime(df.index.astype(str).str[:8], format='%Y%m%d')
                df.index.name = 'date'
                return df
        except Exception as e:
            print(f"QMT获取{code}失败: {e}")

    # 2. Fallback: 生成模拟数据
    import random
    import math
    dates = pd.date_range(end=datetime.datetime.now(), periods=100)
    base_price = 3.0

    data = []
    for i in range(100):
        noise = random.uniform(-0.02, 0.02)
        trend = math.sin(i / 10.0) * 0.5
        price = base_price * (1 + trend + noise)

        data.append({
            'date': dates[i],
            'open': price * (1 - random.uniform(-0.005, 0.005)),
            'high': price * (1 + random.uniform(0, 0.01)),
            'low': price * (1 - random.uniform(0, 0.01)),
            'close': price,
            'volume': 1000000
        })

    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df

def generate_smart_report(plans: List[TradePlan], filename: str):
    """生成智能报告"""
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    content = f"""# 🤖 BIAS-ATR智能交易计划 {today_str}

> 📊 本报告由智能系统自动生成

## 📈 市场概况

| 状态 | 数量 | 说明 |
|------|------|------|
| 🟢 深坑区 | {len([p for p in plans if 'DEEP_DIP' in p.market_status])} | 强烈建议买入 |
| 🟡 黄金区 | {len([p for p in plans if 'GOLD_ZONE' in p.market_status])} | 建议买入 |
| 🔵 震荡区 | {len([p for p in plans if 'OSCILLATION' in p.market_status])} | 网格交易 |
| 🟠 减持区 | {len([p for p in plans if 'REDUCE_ZONE' in p.market_status])} | 建议卖出 |
| 🔴 逃亡区 | {len([p for p in plans if 'ESCAPE' in p.market_status])} | 强烈建议卖出 |

## 📋 详细交易计划

| 代码 | 现价 | BIAS | 状态 | 目标仓位 | 建议操作 | 风险提示 |
|------|------|------|------|----------|----------|----------|
"""

    for plan in plans:
        ops_str = ""
        if plan.suggested_orders:
            ops = [f"{o.direction} {o.amount}股 @{o.price:.3f} ({o.desc})" for o in plan.suggested_orders]
            ops_str = "<br>".join(ops)
        else:
            ops_str = "观望"

        warn_str = "<br>".join(plan.warnings) if plan.warnings else "无"

        status_emoji = {"DEEP_DIP": "🟢", "GOLD_ZONE": "🟡", "OSCILLATION": "🔵",
                       "REDUCE_ZONE": "🟠", "ESCAPE_ZONE": "🔴"}.get(plan.market_status.split()[0], "")

        content += f"| {plan.code} {status_emoji} | {plan.current_price:.3f} | {plan.current_bias:.2f}% | {plan.market_status} | {plan.target_pos_pct*100:.0f}% | {ops_str} | {warn_str} |\n"

    content += f"""

## 💡 操作建议

### 🔥 优先操作
{chr(10).join([f"- **{plan.code}**: {plan.suggested_orders[0].desc}" for plan in plans if plan.suggested_orders and 'CRITICAL' in plan.suggested_orders[0].desc]) if any(plan.suggested_orders and 'CRITICAL' in plan.suggested_orders[0].desc for plan in plans) else "- 无紧急操作"}

### 📊 网格交易
建议对震荡区ETF设置以下网格：
{chr(10).join([f"- **{plan.code}**: 价格间隔 {plan.current_price * 0.01:.3f}" for plan in plans if 'OSCILLATION' in plan.market_status]) if any('OSCILLATION' in plan.market_status for plan in plans) else "- 无震荡区ETF"}

### ⚠️ 风控提醒
{chr(10).join([f"- **{plan.code}**: {warn}" for plan in plans for warn in plan.warnings]) if any(plan.warnings for plan in plans) else "- 当前无特殊风险提示"}

---
*报告生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

def run_wizard():
    """运行智能配置向导"""
    from smart_wizard import SmartConfigWizard
    wizard = SmartConfigWizard()
    wizard.run_wizard()
    input("\n按回车键继续...")

def view_history():
    """查看历史报告"""
    clear_screen()
    print_banner()
    print("📊 历史交易报告")
    print()

    # 查找报告文件
    import glob
    reports = glob.glob("*trade_plan_*.md")
    reports.sort(reverse=True)

    if not reports:
        print("📭 暂无历史报告")
    else:
        print(f"📁 找到 {len(reports)} 个历史报告：")
        print()

        for i, report in enumerate(reports[:10], 1):  # 显示最近10个
            date = report.split('_')[-1].replace('.md', '')
            formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            size = os.path.getsize(report) // 1024
            print(f"  {i}. {formatted_date} ({size}KB) - {report}")

        print("\n💡 要查看详细报告，请打开对应的.md文件")

    input("\n按回车键继续...")

def single_analysis():
    """单独分析ETF"""
    clear_screen()
    print_banner()
    print("🔍 单独ETF分析")
    print()

    code = input("请输入ETF代码 (如 sh510300): ").strip()
    if not code:
        print("❌ 请输入有效代码")
        input("\n按回车键继续...")
        return

    print(f"\n📊 正在分析 {code}...")

    try:
        strategy = GridStrategy()
        df = get_data(code)

        if df is None or df.empty:
            print("❌ 无法获取数据")
            input("\n按回车键继续...")
            return

        mock_holdings = {
            'volume': 10000,
            'available': 10000,
            'avg_cost': df['close'].iloc[-1] * 0.95
        }

        plan = strategy.analyze(code, df, mock_holdings)

        # 显示详细分析结果
        print(f"\n🎯 分析结果：")
        print(f"   当前价格: ¥{plan.current_price:.3f}")
        print(f"   BIAS指标: {plan.current_bias:.2f}%")
        print(f"   市场状态: {plan.market_status}")
        print(f"   目标仓位: {plan.target_pos_pct*100:.0f}%")

        if plan.suggested_orders:
            print(f"\n📋 建议操作 ({len(plan.suggested_orders)}个):")
            for i, order in enumerate(plan.suggested_orders, 1):
                print(f"   {i}. {order.direction} {order.amount}股 @ ¥{order.price:.3f}")
                print(f"      {order.desc}")

        if plan.warnings:
            print(f"\n⚠️ 风险提示:")
            for warning in plan.warnings:
                print(f"   • {warning}")

    except Exception as e:
        print(f"❌ 分析失败: {e}")

    input("\n按回车键继续...")

def show_help():
    """显示帮助信息"""
    clear_screen()
    print_banner()
    print("📖 使用帮助")
    print()

    help_text = """
🎯 系统简介：
   BIAS-ATR-Grid-Trader是一个智能ETF网格交易系统，
   结合BIAS(乖离率)和ATR(平均真实波幅)指标，
   为您提供科学的交易决策。

📊 主要功能：
   1. 一键生成交易计划 - 自动分析所有配置的ETF
   2. 智能配置向导 - 根据您的情况推荐个性化配置
   3. 查看历史报告 - 回顾过去的交易建议
   4. 单独分析ETF - 深度分析单个ETF
   5. 参数设置 - 调整策略参数

⚙️ 策略原理：
   - BIAS指标判断市场位置（深坑、黄金、震荡、减持、逃亡）
   - ATR指标计算合理的网格间距
   - 根据不同区间采用不同的交易策略

🚨 风控机制：
   - 逃顶规则：BIAS > 20/30时强制卖出
   - 熔断机制：单只ETF浮亏超过10%暂停买入
   - 仓位控制：根据市场状态动态调整目标仓位

💡 使用建议：
   1. 初次使用请先运行"智能配置向导"
   2. 每日运行"一键生成交易计划"获取建议
   3. 严格按照建议操作，控制情绪
   4. 定期回顾历史报告，总结经验

📞 技术支持：
   如有问题，请检查：
   - 网络连接是否正常
   - akshare库是否正确安装
   - 配置文件是否有效

祝您投资顺利！📈
"""

    print(help_text)
    input("\n按回车键继续...")

def main():
    """主程序"""
    while True:
        clear_screen()
        print_banner()

        # 显示今日概览
        today = datetime.datetime.now().strftime("%Y-%m-%d %A")
        print(f"🗓️  今天是 {today}")
        print()

        choice = get_user_choice()

        if choice == '0':
            print("\n👋 感谢使用，再见！")
            break
        elif choice == '1':
            smart_generate_daily_plan()
        elif choice == '2':
            run_wizard()
        elif choice == '3':
            view_history()
        elif choice == '4':
            single_analysis()
        elif choice == '5':
            print("⚙️  参数设置功能开发中...")
            input("\n按回车键继续...")
        elif choice == '6':
            show_help()

if __name__ == "__main__":
    main()