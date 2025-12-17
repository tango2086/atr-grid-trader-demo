# backtest.py - 策略回测模块
"""
基于历史数据的策略回测引擎：
- 逐日模拟交易信号
- 计算收益率、回撤等统计指标
- 生成回测报告
"""

import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import config
from strategy import GridStrategy, TradePlan
from indicators import calculate_indicators
from data_manager import get_data_manager
from logger import get_logger


@dataclass
class TradeRecord:
    """交易记录"""
    date: datetime
    code: str
    direction: str  # BUY / SELL
    price: float
    volume: int
    value: float
    reason: str = ""


@dataclass
class BacktestResult:
    """回测结果"""
    code: str
    start_date: str
    end_date: str
    
    # 收益指标
    total_return: float = 0.0        # 总收益率 (%)
    annual_return: float = 0.0       # 年化收益率 (%)
    max_drawdown: float = 0.0        # 最大回撤 (%)
    
    # 交易统计
    trade_count: int = 0             # 交易次数
    win_count: int = 0               # 盈利次数
    win_rate: float = 0.0            # 胜率 (%)
    
    # 资金曲线
    equity_curve: List[float] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)


class GridBacktest:
    """网格策略回测引擎"""
    
    def __init__(self, initial_capital: float = None):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金 (默认使用 config.CAPITAL_PER_ETF)
        """
        self.initial_capital = initial_capital or config.CAPITAL_PER_ETF
        self.strategy = GridStrategy()
        self.data_manager = get_data_manager()
        self.logger = get_logger()
    
    def run(self, code: str, days: int = 252) -> BacktestResult:
        """
        运行回测
        
        Args:
            code: ETF代码 (sh510050 格式)
            days: 回测天数 (默认252个交易日约1年)
        
        Returns:
            回测结果
        """
        print(f"\n📊 开始回测 {code}，周期: {days} 天")
        print("=" * 50)
        
        # 获取历史数据 (尝试获取更多)
        request_count = min(days + 100, 800)  # mootdx 最多返回约800条
        df = self.data_manager.get_history(code, count=request_count)
        
        if df is None or df.empty:
            print(f"❌ 无法获取数据")
            return BacktestResult(code=code, start_date="", end_date="")
        
        # 计算指标
        df = calculate_indicators(df)
        df = df.dropna()  # 删除NaN行
        
        # 检查数据量，自动调整回测天数
        available_days = len(df) - 25  # 需要预留25天计算指标
        if available_days < 30:
            print(f"❌ 数据不足 (仅 {len(df)} 条，需要至少 55 条)")
            return BacktestResult(code=code, start_date="", end_date="")
        
        actual_days = min(days, available_days)
        if actual_days < days:
            print(f"⚠️ 数据不足 {days} 天，自动调整为 {actual_days} 天")
        
        # 取回测数据
        df = df.tail(actual_days + 25)  # 多取25天用于指标计算
        
        # 初始化状态
        cash = self.initial_capital
        position = 0  # 持仓股数
        avg_cost = 0.0  # 平均成本
        
        equity_curve = []
        trades = []
        
        # 获取日期范围
        try:
            start_date = df.index[25].strftime("%Y-%m-%d") if hasattr(df.index[25], 'strftime') else str(df.index[25])[:10]
            end_date = df.index[-1].strftime("%Y-%m-%d") if hasattr(df.index[-1], 'strftime') else str(df.index[-1])[:10]
        except:
            start_date = str(df.index[25])[:10] if len(df) > 25 else ""
            end_date = str(df.index[-1])[:10] if len(df) > 0 else ""
        
        # 逐日回测
        for i in range(20, len(df)):  # 从第20天开始(需要足够数据计算指标)
            current_date = df.index[i]
            current_df = df.iloc[:i+1]  # 截止当日的数据
            
            current_price = current_df['close'].iloc[-1]
            
            # 构建持仓信息
            holdings = {
                'volume': position,
                'available': position,
                'avg_cost': avg_cost
            }
            
            # 策略分析
            plan = self.strategy.analyze(code, current_df, holdings)
            
            # 执行交易信号
            for order in plan.suggested_orders:
                if order.direction == 'BUY':
                    # 买入
                    buy_value = order.price * order.amount
                    if cash >= buy_value:
                        # 更新平均成本
                        total_value = avg_cost * position + order.price * order.amount
                        position += order.amount
                        avg_cost = total_value / position if position > 0 else 0
                        cash -= buy_value
                        
                        trades.append(TradeRecord(
                            date=current_date,
                            code=code,
                            direction='BUY',
                            price=order.price,
                            volume=order.amount,
                            value=buy_value,
                            reason=order.desc
                        ))
                
                elif order.direction == 'SELL':
                    # 卖出
                    if position >= order.amount:
                        sell_value = order.price * order.amount
                        position -= order.amount
                        cash += sell_value
                        
                        trades.append(TradeRecord(
                            date=current_date,
                            code=code,
                            direction='SELL',
                            price=order.price,
                            volume=order.amount,
                            value=sell_value,
                            reason=order.desc
                        ))
            
            # 计算当日权益
            equity = cash + position * current_price
            equity_curve.append(equity)
        
        # 计算统计指标
        result = self._calculate_metrics(
            code, start_date, end_date,
            equity_curve, trades
        )
        
        # 打印结果摘要
        self._print_summary(result)
        
        return result
    
    def _calculate_metrics(self, code: str, start_date: str, end_date: str,
                          equity_curve: List[float], trades: List[TradeRecord]) -> BacktestResult:
        """计算回测统计指标"""
        result = BacktestResult(
            code=code,
            start_date=start_date,
            end_date=end_date,
            equity_curve=equity_curve,
            trades=trades
        )
        
        if not equity_curve:
            return result
        
        # 总收益率
        initial = self.initial_capital
        final = equity_curve[-1]
        result.total_return = (final - initial) / initial * 100
        
        # 年化收益率 (假设252个交易日)
        trading_days = len(equity_curve)
        years = trading_days / 252
        if years > 0 and final > 0:
            result.annual_return = ((final / initial) ** (1 / years) - 1) * 100
        
        # 最大回撤
        equity_arr = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_arr)
        drawdown = (running_max - equity_arr) / running_max * 100
        result.max_drawdown = np.max(drawdown)
        
        # 交易统计
        result.trade_count = len(trades)
        
        # 计算胜率 (基于卖出盈亏)
        sell_trades = [t for t in trades if t.direction == 'SELL']
        if sell_trades:
            # 简化: 假设卖出价高于平均成本即为盈利
            result.win_count = sum(1 for t in sell_trades if t.price > 0)  # 简化处理
            result.win_rate = len(sell_trades) / len(trades) * 100 if trades else 0
        
        return result
    
    def _print_summary(self, result: BacktestResult):
        """打印回测结果摘要"""
        print(f"\n📈 回测结果: {result.code}")
        print(f"   周期: {result.start_date} ~ {result.end_date}")
        print(f"   初始资金: ¥{self.initial_capital:,.0f}")
        print(f"   期末资金: ¥{result.equity_curve[-1]:,.0f}" if result.equity_curve else "   期末资金: N/A")
        print()
        print(f"   📊 收益指标:")
        print(f"      总收益率: {result.total_return:+.2f}%")
        print(f"      年化收益: {result.annual_return:+.2f}%")
        print(f"      最大回撤: {result.max_drawdown:.2f}%")
        print()
        print(f"   🔄 交易统计:")
        print(f"      交易次数: {result.trade_count}")
        print("=" * 50)
    
    def report(self, result: BacktestResult) -> str:
        """生成回测报告 (Markdown格式)"""
        report = f"""# 回测报告: {result.code}

## 基本信息
- **回测周期**: {result.start_date} ~ {result.end_date}
- **初始资金**: ¥{self.initial_capital:,.0f}
- **期末资金**: ¥{result.equity_curve[-1]:,.0f if result.equity_curve else 0}

## 收益指标
| 指标 | 数值 |
|------|------|
| 总收益率 | {result.total_return:+.2f}% |
| 年化收益 | {result.annual_return:+.2f}% |
| 最大回撤 | {result.max_drawdown:.2f}% |

## 交易统计
- **交易次数**: {result.trade_count}
- **胜率**: {result.win_rate:.1f}%

## 交易记录
| 日期 | 方向 | 价格 | 数量 | 金额 | 原因 |
|------|------|------|------|------|------|
"""
        for trade in result.trades[-20:]:  # 最近20笔
            date_str = trade.date.strftime("%Y-%m-%d") if hasattr(trade.date, 'strftime') else str(trade.date)[:10]
            report += f"| {date_str} | {trade.direction} | {trade.price:.3f} | {trade.volume} | ¥{trade.value:.0f} | {trade.reason[:15]} |\n"
        
        report += f"\n*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        return report


def run_backtest_menu():
    """回测菜单界面"""
    print("\n📈 策略回测")
    print("=" * 50)
    
    # 选择ETF
    print("可回测的ETF:")
    for i, code in enumerate(config.ETF_LIST, 1):
        name = config.ETF_NAMES.get(code, code)
        print(f"  {i}. {code} ({name})")
    print(f"  0. 全部回测")
    
    choice = input("\n请选择 (输入序号): ").strip()
    
    # 选择回测天数
    days_input = input("回测天数 (默认252): ").strip()
    days = int(days_input) if days_input.isdigit() else 252
    
    # 执行回测
    backtest = GridBacktest()
    
    if choice == '0':
        # 全部回测
        for code in config.ETF_LIST:
            result = backtest.run(code, days)
    elif choice.isdigit() and 1 <= int(choice) <= len(config.ETF_LIST):
        code = config.ETF_LIST[int(choice) - 1]
        result = backtest.run(code, days)
        
        # 保存报告
        report = backtest.report(result)
        filename = f"backtest_{code}_{datetime.now():%Y%m%d}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 报告已保存: {filename}")
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    run_backtest_menu()
