# smart_wizard.py
import sys
from typing import Dict, List, Tuple
import datetime

class SmartConfigWizard:
    """智能配置向导 - 让用户轻松设置交易策略"""

    def __init__(self):
        self.user_profile = {}
        self.risk_tolerance = "medium"

    def welcome(self):
        """欢迎界面"""
        print("=" * 60)
        print("🤖 BIAS-ATR-Grid-Trader 智能配置向导")
        print("=" * 60)
        print("让我们一起为您定制专属的ETF网格交易策略！")
        print()

    def get_user_profile(self) -> Dict:
        """获取用户画像"""
        print("📋 首先，让我们了解一下您的情况：")
        print()

        # 1. 投资经验
        while True:
            experience = input("您有几年的投资经验？(0=新手, 1-3=进阶, 3+=经验丰富): ").strip()
            if experience in ['0', '1', '2', '3'] or experience.isdigit() and int(experience) >= 3:
                self.user_profile['experience'] = int(experience) if experience.isdigit() else 0
                break
            print("请输入有效选项")

        # 2. 总资金
        while True:
            try:
                capital = float(input("您计划投入的总资金是多少？(例如: 50000): ").strip())
                if capital >= 10000:
                    self.user_profile['total_capital'] = capital
                    break
                else:
                    print("建议至少投入1万元以上以获得更好的分散效果")
            except ValueError:
                print("请输入有效数字")

        # 3. 风险偏好
        print("\n您的风险偏好如何？")
        print("1. 保守型 - 稳健收益，能承受较小回撤")
        print("2. 平衡型 - 追求中等收益，能承受中等回撤")
        print("3. 激进型 - 追求高收益，能承受较大回撤")

        while True:
            risk_choice = input("请选择(1-3): ").strip()
            if risk_choice in ['1', '2', '3']:
                risk_map = {'1': 'conservative', '2': 'medium', '3': 'aggressive'}
                self.risk_tolerance = risk_map[risk_choice]
                break
            print("请输入1-3")

        # 4. 投资目标
        print("\n您的投资目标主要是？")
        print("1. 长期稳健增值")
        print("2. 中期趋势跟踪")
        print("3. 短期波段操作")

        while True:
            goal = input("请选择(1-3): ").strip()
            if goal in ['1', '2', '3']:
                goal_map = {'1': 'long_term', '2': 'medium_term', '3': 'short_term'}
                self.user_profile['investment_goal'] = goal_map[goal]
                break
            print("请输入1-3")

        return self.user_profile

    def recommend_etf_allocation(self) -> List[Dict]:
        """推荐ETF配置"""
        print("\n🎯 基于您的情况，我推荐以下ETF配置：")
        print()

        if self.risk_tolerance == 'conservative':
            allocation = [
                {"code": "sh510300", "name": "沪深300ETF", "allocation": 0.4, "reason": "大盘蓝筹，稳健"},
                {"code": "sh518880", "name": "黄金ETF", "allocation": 0.2, "reason": "抗通胀，避险"},
                {"code": "sh512890", "name": "红利低波ETF", "allocation": 0.2, "reason": "稳定分红"},
                {"code": "sh510500", "name": "中证500ETF", "allocation": 0.2, "reason": "中等成长"}
            ]
        elif self.risk_tolerance == 'aggressive':
            allocation = [
                {"code": "sz159915", "name": "创业板ETF", "allocation": 0.3, "reason": "高成长潜力"},
                {"code": "sh512480", "name": "半导体ETF", "allocation": 0.3, "reason": "科技成长"},
                {"code": "sh512880", "name": "证券ETF", "allocation": 0.2, "reason": "高波动机会"},
                {"code": "sh510300", "name": "沪深300ETF", "allocation": 0.2, "reason": "稳定器"}
            ]
        else:  # medium
            allocation = [
                {"code": "sh510300", "name": "沪深300ETF", "allocation": 0.3, "reason": "核心配置"},
                {"code": "sh510500", "name": "中证500ETF", "allocation": 0.25, "reason": "均衡成长"},
                {"code": "sz159915", "name": "创业板ETF", "allocation": 0.25, "reason": "成长动力"},
                {"code": "sh518880", "name": "黄金ETF", "allocation": 0.2, "reason": "分散化配置"}
            ]

        for i, etf in enumerate(allocation, 1):
            amount = self.user_profile['total_capital'] * etf['allocation']
            print(f"{i}. {etf['name']} ({etf['code']})")
            print(f"   配置比例: {etf['allocation']*100:.0f}% | 金额: ¥{amount:,.0f}")
            print(f"   推荐理由: {etf['reason']}")
            print()

        return allocation

    def suggest_strategy_parameters(self) -> Dict:
        """推荐策略参数"""
        print("⚙️ 推荐策略参数设置：")
        print()

        # 根据风险偏好调整参数
        if self.risk_tolerance == 'conservative':
            params = {
                'grid_count': 3,  # 较少网格
                'min_profit_pct': 0.015,  # 更高最小利润要求
                'max_drawdown': -0.08,  # 更严格风控
                'rebalance_freq': 'monthly'  # 更频繁再平衡
            }
        elif self.risk_tolerance == 'aggressive':
            params = {
                'grid_count': 5,  # 更多网格
                'min_profit_pct': 0.008,  # 较低最小利润要求
                'max_drawdown': -0.15,  # 更宽松风控
                'rebalance_freq': 'quarterly'  # 较少再平衡
            }
        else:  # medium
            params = {
                'grid_count': 4,
                'min_profit_pct': 0.01,
                'max_drawdown': -0.10,
                'rebalance_freq': 'monthly'
            }

        print(f"📊 网格层数: {params['grid_count']}层")
        print(f"💰 最小利润要求: {params['min_profit_pct']*100:.1f}%")
        print(f"🛡️ 最大回撤限制: {params['max_drawdown']*100:.0f}%")
        print(f"🔄 再平衡频率: {params['rebalance_freq']}")
        print()

        return params

    def generate_smart_config(self) -> str:
        """生成智能配置文件"""
        etf_list = self.recommend_etf_allocation()
        params = self.suggest_strategy_parameters()

        # 根据风险偏好获取参数值
        bias_params = {
            "conservative": {"DEEP_DIP": -8.0, "GOLD_ZONE_UPPER": -2.0, "OSCILLATION_UPPER": 6.0, "REDUCE_ZONE_UPPER": 15.0},
            "medium": {"DEEP_DIP": -10.0, "GOLD_ZONE_UPPER": -3.0, "OSCILLATION_UPPER": 8.0, "REDUCE_ZONE_UPPER": 20.0},
            "aggressive": {"DEEP_DIP": -12.0, "GOLD_ZONE_UPPER": -4.0, "OSCILLATION_UPPER": 10.0, "REDUCE_ZONE_UPPER": 25.0}
        }

        position_params = {
            "conservative": {"DEEP_DIP": 0.8, "GOLD_ZONE": 0.6, "OSCILLATION": 0.4, "REDUCE_ZONE": 0.2},
            "medium": {"DEEP_DIP": 0.9, "GOLD_ZONE": 0.7, "OSCILLATION": 0.5, "REDUCE_ZONE": 0.3},
            "aggressive": {"DEEP_DIP": 0.95, "GOLD_ZONE": 0.8, "OSCILLATION": 0.6, "REDUCE_ZONE": 0.4}
        }

        grid_params = {
            "conservative": 1.2,
            "medium": 1.5,
            "aggressive": 1.8
        }

        current_bias = bias_params[self.risk_tolerance]
        current_position = position_params[self.risk_tolerance]
        current_grid = grid_params[self.risk_tolerance]

        config_content = f'''# smart_config.py
# 智能生成的配置文件 - {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# 用户画像
USER_PROFILE = {self.user_profile}
RISK_TOLERANCE = "{self.risk_tolerance}"

# 智能ETF配置
SMART_ETF_LIST = {etf_list}

# 推荐策略参数
STRATEGY_PARAMS = {params}

# 资金分配
TOTAL_CAPITAL = {self.user_profile['total_capital']}
ETF_COUNT = len(SMART_ETF_LIST)
CAPITAL_PER_ETF = TOTAL_CAPITAL / ETF_COUNT

# BIAS阈值 (根据风险偏好调整)
class BIAS_THRESHOLDS:
    DEEP_DIP = {current_bias["DEEP_DIP"]}
    GOLD_ZONE_UPPER = {current_bias["GOLD_ZONE_UPPER"]}
    OSCILLATION_UPPER = {current_bias["OSCILLATION_UPPER"]}
    REDUCE_ZONE_UPPER = {current_bias["REDUCE_ZONE_UPPER"]}

    ESCAPE_TOP_EXTREME = 30.0
    ESCAPE_TOP_HIGH = 20.0
    TREND_REVERSAL = 3.0

# 目标仓位 (根据风险偏好调整)
class TARGET_POSITION:
    DEEP_DIP = {current_position["DEEP_DIP"]}
    GOLD_ZONE = {current_position["GOLD_ZONE"]}
    OSCILLATION = {current_position["OSCILLATION"]}
    REDUCE_ZONE = {current_position["REDUCE_ZONE"]}
    ESCAPE_ZONE = 0.0

# 网格参数
GRID_COEFFICIENT = {{
    'DEEP_DIP': {current_grid},
    'OSCILLATION': 1.0,
}}

MIN_PROFIT_PCT = {params['min_profit_pct']}
LOT_SIZE = 100
MAX_DRAWDOWN_LIMIT = {params['max_drawdown']}

# ETF代码列表 (兼容原系统)
ETF_LIST = [etf['code'] for etf in SMART_ETF_LIST]
'''

        return config_content

    def run_wizard(self):
        """运行完整向导"""
        self.welcome()
        self.get_user_profile()
        self.recommend_etf_allocation()
        self.suggest_strategy_parameters()

        print("🎉 配置完成！")
        save_choice = input("\n是否保存智能配置？(y/n): ").strip().lower()

        if save_choice == 'y':
            config_content = self.generate_smart_config()
            with open('smart_config.py', 'w', encoding='utf-8') as f:
                f.write(config_content)
            print("✅ 智能配置已保存到 smart_config.py")
            print("📝 您现在可以使用 'python smart_main.py' 来运行智能版本")
        else:
            print("配置未保存")

if __name__ == "__main__":
    wizard = SmartConfigWizard()
    wizard.run_wizard()