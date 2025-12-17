# visualizer.py - 可视化报告生成器
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from typing import List, Dict
import config
from strategy import GridStrategy, TradePlan

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class TradingVisualizer:
    """交易可视化工具"""

    def __init__(self):
        self.colors = {
            'deep_dip': '#2E8B57',      # 深绿
            'gold_zone': '#FFD700',     # 金色
            'oscillation': '#4169E1',   # 蓝色
            'reduce_zone': '#FF8C00',   # 橙色
            'escape_zone': '#DC143C'    # 红色
        }

    def generate_market_heatmap(self, plans: List[TradePlan], save_path: str = None):
        """生成市场热力图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8))

        # 1. BIAS分布图
        codes = [plan.code for plan in plans]
        biases = [plan.current_bias for plan in plans]
        colors = []

        for bias in biases:
            if bias < -10:
                colors.append(self.colors['deep_dip'])
            elif bias < -3:
                colors.append(self.colors['gold_zone'])
            elif bias < 8:
                colors.append(self.colors['oscillation'])
            elif bias < 20:
                colors.append(self.colors['reduce_zone'])
            else:
                colors.append(self.colors['escape_zone'])

        bars = ax1.barh(codes, biases, color=colors)
        ax1.set_xlabel('BIAS (%)')
        ax1.set_title('ETF BIAS 分布图')
        ax1.axvline(x=-10, color='gray', linestyle='--', alpha=0.5, label='深坑区')
        ax1.axvline(x=-3, color='gray', linestyle='--', alpha=0.5, label='黄金区')
        ax1.axvline(x=8, color='gray', linestyle='--', alpha=0.5, label='震荡区')
        ax1.axvline(x=20, color='gray', linestyle='--', alpha=0.5, label='减持区')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 添加数值标签
        for i, (bar, bias) in enumerate(zip(bars, biases)):
            ax1.text(bar.get_width() + (0.5 if bias >= 0 else -0.5),
                    bar.get_y() + bar.get_height()/2,
                    f'{bias:.1f}%', ha='left' if bias >= 0 else 'right', va='center')

        # 2. 目标仓位图
        target_positions = [plan.target_pos_pct * 100 for plan in plans]
        colors2 = [self.colors['deep_dip'] if pos >= 80 else
                  self.colors['gold_zone'] if pos >= 60 else
                  self.colors['oscillation'] if pos >= 40 else
                  self.colors['reduce_zone'] if pos >= 20 else
                  self.colors['escape_zone'] for pos in target_positions]

        bars2 = ax2.barh(codes, target_positions, color=colors2)
        ax2.set_xlabel('目标仓位 (%)')
        ax2.set_title('ETF 目标仓位')
        ax2.set_xlim(0, 100)
        ax2.grid(True, alpha=0.3)

        # 添加数值标签
        for i, (bar, pos) in enumerate(zip(bars2, target_positions)):
            ax2.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                    f'{pos:.0f}%', ha='left', va='center')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 市场热力图已保存: {save_path}")
        else:
            plt.show()

        plt.close()

    def generate_strategy_pie_chart(self, plans: List[TradePlan], save_path: str = None):
        """生成策略分布饼图"""
        # 统计各种状态的ETF数量
        status_count = {}
        for plan in plans:
            status = plan.market_status.split()[0]
            status_count[status] = status_count.get(status, 0) + 1

        # 准备数据
        labels = []
        sizes = []
        colors = []
        status_map = {
            'DEEP_DIP': ('深坑区(强烈买入)', self.colors['deep_dip']),
            'GOLD_ZONE': ('黄金区(建议买入)', self.colors['gold_zone']),
            'OSCILLATION': ('震荡区(网格交易)', self.colors['oscillation']),
            'REDUCE_ZONE': ('减持区(建议卖出)', self.colors['reduce_zone']),
            'ESCAPE_ZONE': ('逃亡区(强烈卖出)', self.colors['escape_zone'])
        }

        for status, count in status_count.items():
            if status in status_map:
                labels.append(f"{status_map[status][0]}\n({count}只)")
                sizes.append(count)
                colors.append(status_map[status][1])

        # 创建饼图
        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                          startangle=90, textprops={'fontsize': 10})

        # 美化文字
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_weight('bold')

        ax.set_title(f'ETF策略分布图 ({datetime.now().strftime("%Y-%m-%d")})',
                    fontsize=14, fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 策略分布图已保存: {save_path}")
        else:
            plt.show()

        plt.close()

    def generate_price_chart(self, code: str, df: pd.DataFrame, plan: TradePlan, save_path: str = None):
        """生成价格走势图"""
        if df is None or df.empty:
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10),
                                       gridspec_kw={'height_ratios': [2, 1]})

        # 1. 价格和均线图
        ax1.plot(df.index, df['close'], label='收盘价', linewidth=1.5, color='blue')
        ax1.plot(df.index, df['ma_20'], label='MA20', linewidth=1, color='orange')

        # 标记当前价格
        current_price = df['close'].iloc[-1]
        current_ma = df['ma_20'].iloc[-1]
        ax1.scatter(df.index[-1], current_price, color='red', s=50, zorder=5)
        ax1.annotate(f'¥{current_price:.3f}',
                    (df.index[-1], current_price),
                    xytext=(10, 10), textcoords='offset points')

        # BIAS区域着色
        ax1_twin = ax1.twinx()

        # 创建BIAS区域颜色带
        for i in range(len(df) - 1):
            bias_val = df['bias_20'].iloc[i]
            if bias_val < -10:
                color = self.colors['deep_dip']
                alpha = 0.2
            elif bias_val < -3:
                color = self.colors['gold_zone']
                alpha = 0.15
            elif bias_val < 8:
                color = self.colors['oscillation']
                alpha = 0.1
            elif bias_val < 20:
                color = self.colors['reduce_zone']
                alpha = 0.15
            else:
                color = self.colors['escape_zone']
                alpha = 0.2

            ax1.axvspan(df.index[i], df.index[i+1], alpha=alpha, color=color)

        ax1.set_title(f'{code} 价格走势与BIAS区域', fontsize=14, fontweight='bold')
        ax1.set_ylabel('价格 (¥)')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # 2. BIAS指标图
        ax2.plot(df.index, df['bias_20'], label='BIAS_20', linewidth=1.5, color='green')
        ax2.axhline(y=-10, color='gray', linestyle='--', alpha=0.7, label='深坑区')
        ax2.axhline(y=-3, color='gray', linestyle='--', alpha=0.7, label='黄金区')
        ax2.axhline(y=8, color='gray', linestyle='--', alpha=0.7, label='震荡区')
        ax2.axhline(y=20, color='gray', linestyle='--', alpha=0.7, label='减持区')

        # 标记当前BIAS
        current_bias = df['bias_20'].iloc[-1]
        ax2.scatter(df.index[-1], current_bias, color='red', s=50, zorder=5)
        ax2.annotate(f'{current_bias:.1f}%',
                    (df.index[-1], current_bias),
                    xytext=(10, 10), textcoords='offset points')

        ax2.set_ylabel('BIAS (%)')
        ax2.set_xlabel('日期')
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)

        # 添加策略建议文本框
        strategy_text = f"当前状态: {plan.market_status}\n目标仓位: {plan.target_pos_pct*100:.0f}%"
        if plan.suggested_orders:
            strategy_text += f"\n建议操作: {len(plan.suggested_orders)}个"

        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax1.text(0.02, 0.98, strategy_text, transform=ax1.transAxes, fontsize=10,
                verticalalignment='top', bbox=props)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 {code} 价格走势图已保存: {save_path}")
        else:
            plt.show()

        plt.close()

    def generate_comprehensive_report(self, plans: List[TradePlan], data_dict: Dict[str, pd.DataFrame]):
        """生成综合可视化报告"""
        print("🎨 正在生成可视化报告...")

        # 创建报告目录
        report_dir = f"visual_report_{datetime.now().strftime('%Y%m%d')}"
        os.makedirs(report_dir, exist_ok=True)

        # 1. 市场热力图
        self.generate_market_heatmap(plans, os.path.join(report_dir, 'market_heatmap.png'))

        # 2. 策略分布饼图
        self.generate_strategy_pie_chart(plans, os.path.join(report_dir, 'strategy_pie.png'))

        # 3. 个股价格走势图
        for plan in plans:
            if plan.code in data_dict:
                self.generate_price_chart(plan.code, data_dict[plan.code], plan,
                                        os.path.join(report_dir, f'{plan.code}_chart.png'))

        # 4. 生成HTML报告
        self.generate_html_report(plans, report_dir)

        print(f"✅ 可视化报告已生成: {report_dir}/")
        print(f"   📊 市场热力图: {report_dir}/market_heatmap.png")
        print(f"   🥧 策略分布图: {report_dir}/strategy_pie.png")
        print(f"   📈 个股走势图: {report_dir}/*_chart.png")
        print(f"   🌐 HTML报告: {report_dir}/report.html")

    def generate_html_report(self, plans: List[TradePlan], report_dir: str):
        """生成HTML报告"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>BIAS-ATR 智能交易报告 {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; }}
        .header {{ text-align: center; color: #333; margin-bottom: 30px; }}
        .section {{ margin: 30px 0; }}
        .chart {{ text-align: center; margin: 20px 0; }}
        .chart img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 BIAS-ATR 智能交易报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="section">
        <h2>📊 市场概览</h2>
        <div class="chart">
            <img src="market_heatmap.png" alt="市场热力图">
        </div>
        <div class="chart">
            <img src="strategy_pie.png" alt="策略分布图">
        </div>
    </div>

    <div class="section">
        <h2>📈 个股分析</h2>
"""

        # 添加个股分析
        for plan in plans:
            html_content += f"""
        <h3>{plan.code}</h3>
        <div class="summary">
            <p><strong>当前价格:</strong> ¥{plan.current_price:.3f}</p>
            <p><strong>BIAS指标:</strong> {plan.current_bias:.2f}%</p>
            <p><strong>市场状态:</strong> {plan.market_status}</p>
            <p><strong>目标仓位:</strong> {plan.target_pos_pct*100:.0f}%</p>
        </div>
        <div class="chart">
            <img src="{plan.code}_chart.png" alt="{plan.code} 价格走势">
        </div>
"""

        html_content += """
    </div>

    <div class="section">
        <h2>💡 投资建议</h2>
        <div class="summary">
            <p>本报告基于BIAS乖离率和ATR波动率指标生成，仅供参考。</p>
            <p>投资有风险，决策需谨慎。请根据自身风险承受能力合理配置资产。</p>
        </div>
    </div>

</body>
</html>
"""

        with open(os.path.join(report_dir, 'report.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)

def generate_visual_report():
    """生成可视化报告的便捷函数"""
    try:
        # 获取数据
        etf_list = config.ETF_CODE_LIST if hasattr(config, 'ETF_CODE_LIST') else config.ETF_LIST
        strategy = GridStrategy()
        plans = []
        data_dict = {}

        print("📊 正在分析数据...")

        for code in etf_list:
            try:
                # 模拟获取数据（实际应用中应该用真实数据）
                import random
                import math

                # 生成模拟数据
                dates = pd.date_range(end=datetime.now(), periods=100)
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

                # 计算指标
                from indicators import calculate_indicators
                df = calculate_indicators(df)

                data_dict[code] = df

                # 模拟持仓
                mock_holdings = {
                    'volume': 10000,
                    'available': 10000,
                    'avg_cost': df['close'].iloc[-1] * 0.95
                }

                # 分析
                plan = strategy.analyze(code, df, mock_holdings)
                plans.append(plan)

            except Exception as e:
                print(f"⚠️ {code} 分析失败: {e}")

        # 生成可视化报告
        visualizer = TradingVisualizer()
        visualizer.generate_comprehensive_report(plans, data_dict)

    except Exception as e:
        print(f"❌ 生成可视化报告失败: {e}")

if __name__ == "__main__":
    generate_visual_report()