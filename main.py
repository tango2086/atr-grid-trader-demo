# main.py - 交易计划生成器
import pandas as pd
import datetime
import config
from strategy import GridStrategy, TradePlan
from data_manager import get_data_manager
from logger import get_logger

# 初始化日志
logger = get_logger()

# 获取数据管理器
data_manager = get_data_manager()

def get_data(code: str) -> pd.DataFrame:
    """获取 ETF 历史数据 (使用统一数据管理器)"""
    return data_manager.get_history(code)

def run():
    print("=== BIAS-ATR-Grid-Trader Starting ===")
    strategy = GridStrategy()
    
    # 获取今日日期用于文件名
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    report_file = f"trade_plan_{today_str}.md"
    
    report_lines = [f"# 交易计划日报 {today_str}", "", "| 代码 | 现价 | BIAS | 状态 | 目标仓位 | 建议操作 | 风险提示 |", "|---|---|---|---|---|---|---|"]
    
    for code in config.ETF_LIST:
        try:
            df = get_data(code)
            if df is None or df.empty:
                print(f"Error: No data for {code}")
                continue
            
            # 使用真实持仓数据
            # 从config.REAL_HOLDINGS读取实际持仓信息
            real_holdings = getattr(config, 'REAL_HOLDINGS', {})
            holdings = real_holdings.get(code, {
                'volume': 0, 
                'available': 0, 
                'avg_cost': 0
            })
            
            plan: TradePlan = strategy.analyze(code, df, holdings)
            
            # 格式化输出
            ops_str = ""
            if plan.suggested_orders:
                ops = [f"{o.direction} {o.amount}股 @ {o.price:.3f} ({o.desc})" for o in plan.suggested_orders]
                ops_str = "<br>".join(ops)
            else:
                ops_str = "无操作"
                
            warn_str = "<br>".join(plan.warnings) if plan.warnings else "无"
            
            row = f"| {code} | {plan.current_price:.3f} | {plan.current_bias:.2f}% | {plan.market_status} | {plan.target_pos_pct*100:.0f}% | {ops_str} | {warn_str} |"
            report_lines.append(row)
            
            print(f"[{code}] Analyzed: {plan.market_status}, Orders: {len(plan.suggested_orders)}")
            
        except Exception as e:
            print(f"Error analyzing {code}: {e}")
            import traceback
            traceback.print_exc()

    # 保存报告
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"\nReport saved to {report_file}")
    # 同时输出到控制台
    # print("\n".join(report_lines))

if __name__ == "__main__":
    run()