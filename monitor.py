# monitor.py - 实时监控主模块
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import config
from strategy import GridStrategy, TradePlan, TradeOrder
from notifier import get_notifier
from trader import get_trader
from data_manager import get_data_manager
from logger import get_logger
from persistence import grid_state_manager

# 初始化数据管理器和日志
data_manager = get_data_manager()
logger = get_logger()


class GridMonitor:
    """网格监控器"""
    
    def __init__(self):
        self.conf = config
        self.monitor_conf = config.MONITOR_CONFIG
        self.strategy = GridStrategy()
        self.notifier = get_notifier()
        self.trader = get_trader()
        
        # 状态追踪
        self.last_prices: Dict[str, float] = {}
        self.pending_orders: Dict[str, List[TradeOrder]] = {}  # 待触发订单
        self.triggered_orders: Dict[str, set] = {}  # 已触发的价格点
        
        self._running = False
    
    def _convert_code(self, code: str) -> str:
        """转换代码格式: sh510050 -> 510050.SH"""
        return code[2:] + '.' + code[:2].upper()
    
    def _is_trading_time(self) -> bool:
        """判断是否在交易时间"""
        # TODO: 测试模式 - 始终返回 True，正式使用时需改回
        return True
        
        # --- 正式逻辑 (测试完成后取消注释) ---
        # now = datetime.now()
        # current_time = now.strftime("%H:%M")
        # 
        # # 周末不交易
        # if now.weekday() >= 5:
        #     return False
        # 
        # # 交易时段: 9:30-11:30, 13:00-15:00
        # if "09:30" <= current_time <= "11:30":
        #     return True
        # if "13:00" <= current_time <= "15:00":
        #     return True
        # 
        # return False
    
    def get_realtime_data(self, codes: List[str]) -> Dict[str, Dict]:
        """获取实时行情 (使用统一数据管理器)"""
        return data_manager.get_realtime(codes)
    
    def get_hist_data(self, code: str, count: int = 50) -> pd.DataFrame:
        """获取历史数据 (使用统一数据管理器)"""
        return data_manager.get_history(code, count)
    
    def analyze_all(self) -> List[TradePlan]:
        """分析所有ETF"""
        plans = []
        
        for code in self.conf.ETF_LIST:
            try:
                # 获取历史数据
                df = self.get_hist_data(code)
                if df.empty:
                    continue
                
                # 获取持仓
                holdings = self.conf.REAL_HOLDINGS.get(code, {
                    'volume': 0, 'available': 0, 'avg_cost': 0
                })
                
                # 分析
                plan = self.strategy.analyze(code, df, holdings)
                plans.append(plan)
                
                # 保存待触发订单
                self.pending_orders[code] = plan.suggested_orders
                
            except Exception as e:
                print(f"分析 {code} 失败: {e}")
        
        return plans
    
    def check_triggers(self, realtime_data: Dict) -> List[Dict]:
        """检查价格触发"""
        triggered = []
        alert_pct = self.monitor_conf.PRICE_ALERT_PCT
        
        for code, pending in self.pending_orders.items():
            if code not in realtime_data:
                continue
            
            current_price = realtime_data[code].get('price', 0)
            if current_price <= 0:
                continue
            
            # 初始化已触发集合 (逻辑已迁移至数据库，此段保留仅为兼容，实际判重走DB)
            # if code not in self.triggered_orders:
            #     self.triggered_orders[code] = set()
            
            for order in pending:
                # 生成唯一标识
                # order_key = f"{order.direction}_{order.price:.3f}"
                
                # [PERSISTENCE UPDATE] 检查是否已从数据库触发
                today_str = datetime.now().strftime('%Y-%m-%d')
                if grid_state_manager.is_grid_triggered(today_str, code, order.price, order.direction):
                    continue
                
                # 计算偏离度
                deviation = abs(current_price - order.price) / order.price
                
                if deviation <= alert_pct:
                    # 触发!
                    triggered.append({
                        'code': code,
                        'order': order,
                        'current_price': current_price,
                        'target_price': order.price
                    })
                    
                    # [PERSISTENCE UPDATE] 标记为已触发
                    grid_state_manager.mark_grid_triggered(today_str, code, order.price, order.direction)
                    
                    # 发送通知
                    self.notifier.signal_alert(
                        code, 
                        order.direction, 
                        current_price,
                        f"{order.desc} (目标价 {order.price:.3f})"
                    )
                    
                    # 尝试自动下单
                    if self.conf.TRADE_CONFIG.AUTO_TRADE_ENABLED:
                        result = self.trader.place_order(
                            code, 
                            order.direction, 
                            order.price,  # 用网格价格
                            order.amount
                        )
                        print(f"自动下单结果: {result.message}")
        
        return triggered
    
    def print_status(self, plans: List[TradePlan], realtime_data: Dict):
        """打印当前状态 - 分屏版"""
        now = datetime.now().strftime("%H:%M:%S")
        
        # 状态中文映射
        status_cn = {
            "DEEP_DIP": "🟢深坑",
            "GOLD_ZONE": "🟡黄金", 
            "OSCILLATION": "🔵震荡",
            "REDUCE_ZONE": "🟠减持",
            "ESCAPE_ZONE": "🔴逃顶",
            "ESCAPE_CRAZY": "🔴疯狂",
            "ESCAPE_HIGH": "🔴逃顶",
            "ESCAPE_DIVERGENCE": "🔴背离"
        }
        
        auto_trade_icon = "✅" if self.conf.TRADE_CONFIG.AUTO_TRADE_ENABLED else "❌"
        
        print(f"\n📊 BIAS-ATR 监控 | {now} | 刷新: {self.monitor_conf.REFRESH_INTERVAL}s | 自动下单: {auto_trade_icon}")
        print(f"{'='*85}")
        
        # ========== 持仓概览区 ==========
        print(f"\n🏷️  持仓概览")
        print(f"{'代码':<10} {'名称':<6} {'现价':>6} {'持仓':>6} {'成本':>6} {'市值':>8} {'盈亏':>8} {'涨跌':>8} {'BIAS':>8} {'目标':>5}")
        print(f"{'-'*90}")
        
        total_value = 0
        total_profit = 0
        grid_data = []  # 收集网格数据用于第二个表
        
        for plan in plans:
            code = plan.code
            name = getattr(self.conf, 'ETF_NAMES', {}).get(code, code[-6:])
            rt = realtime_data.get(code, {})
            price = rt.get('price', plan.current_price)
            
            # 持仓信息
            holdings = self.conf.REAL_HOLDINGS.get(code, {})
            hold_vol = holdings.get('volume', 0)
            avg_cost = holdings.get('avg_cost', 0)
            
            # 计算
            change_pct = 0
            profit = 0
            if avg_cost > 0 and hold_vol > 0:
                change_pct = (price - avg_cost) / avg_cost * 100
                profit = (price - avg_cost) * hold_vol
            
            market_value = price * hold_vol
            total_value += market_value
            total_profit += profit
            
            # 格式化持仓数
            if hold_vol >= 10000:
                vol_str = f"{hold_vol/1000:.0f}k"
            else:
                vol_str = f"{hold_vol}"
            
            # 涨跌幅字符串
            change_sign = "+" if change_pct >= 0 else ""
            change_str = f"{change_sign}{change_pct:.1f}%"
            
            # 盈亏字符串
            profit_sign = "+" if profit >= 0 else ""
            profit_str = f"{profit_sign}{profit:,.0f}"
            
            # BIAS 字符串
            bias_sign = "+" if plan.current_bias >= 0 else ""
            bias_str = f"{bias_sign}{plan.current_bias:.2f}%"
            
            print(f"{code:<10} {name:<6} {price:>6.3f} {vol_str:>6} {avg_cost:>6.2f} {market_value:>8,.0f} {profit_str:>8} {change_str:>8} {bias_str:>8} {plan.target_pos_pct*100:>4.0f}%")
            
            # 收集网格数据
            pending = self.pending_orders.get(code, [])
            buy_orders = [o for o in pending if o.direction == 'BUY']
            sell_orders = [o for o in pending if o.direction == 'SELL']
            status_key = plan.market_status.split()[0] if plan.market_status else "UNKNOWN"
            status_str = status_cn.get(status_key, f"⚪{status_key[:4]}")
            grid_data.append({
                'code': code,
                'name': name,
                'buy': buy_orders,
                'sell': sell_orders,
                'status': status_str,
                'support': plan.support,
                'resistance': plan.resistance,
                'price': price
            })
        
        # ========== 网格挂单区 ==========
        print(f"\n📈 网格挂单 (支撑/阻力位参考)")
        print(f"{'代码':<10} {'支撑':>6} {'买单':>10} {'现价':>6} {'卖单':>10} {'阻力':>6} {'状态':>8}")
        print(f"{'-'*75}")
        
        total_buy = 0
        total_sell = 0
        
        for g in grid_data:
            # 买入挂单
            if g['buy']:
                o = g['buy'][0]
                vol = f"{o.amount/1000:.0f}k" if o.amount >= 1000 else str(o.amount)
                buy_str = f"{o.price:.2f}×{vol}"
                total_buy += 1
            else:
                buy_str = "-"
            
            # 卖出挂单
            if g['sell']:
                o = g['sell'][0]
                vol = f"{o.amount/1000:.0f}k" if o.amount >= 1000 else str(o.amount)
                sell_str = f"{o.price:.2f}×{vol}"
                total_sell += 1
            else:
                sell_str = "-"
            
            # 支撑/阻力位
            support_str = f"{g['support']:.2f}" if g['support'] > 0 else "-"
            resist_str = f"{g['resistance']:.2f}" if g['resistance'] > 0 else "-"
            
            print(f"{g['code']:<10} {support_str:>6} {buy_str:>10} {g['price']:>6.3f} {sell_str:>10} {resist_str:>6} {g['status']:>8}")
        
        # ========== 汇总区 ==========
        print(f"\n📊 资金状况")
        
        # 计算资金利用率
        total_capital = self.conf.TOTAL_CAPITAL
        cash = total_capital - total_value
        position_pct = total_value / total_capital * 100 if total_capital > 0 else 0
        cash_pct = 100 - position_pct
        
        # 计算待触发订单资金需求
        buy_capital_needed = 0
        sell_capital_release = 0
        for orders in self.pending_orders.values():
            for o in orders:
                order_value = o.price * o.amount
                if o.direction == 'BUY':
                    buy_capital_needed += order_value
                else:
                    sell_capital_release += order_value
        
        # 盈亏率
        profit_pct = total_profit / total_capital * 100 if total_capital > 0 else 0
        profit_icon = "📈" if total_profit > 0 else ("📉" if total_profit < 0 else "➖")
        profit_sign = "+" if total_profit >= 0 else ""
        
        print(f"💰 资产净值: ¥{total_capital:,.0f} (持仓: {position_pct:.0f}% | 现金: {cash_pct:.0f}%)")
        print(f"{profit_icon} 累计盈亏: {profit_sign}{profit_pct:.2f}% ({profit_sign}¥{total_profit:,.0f})")
        print(f"⚡ 挂单: {total_buy}买待命 (需¥{buy_capital_needed/1000:.1f}k) | {total_sell}卖待命 (可释放¥{sell_capital_release/1000:.1f}k)")
        
        # 风险警告
        warnings = [(plan.code, warn) for plan in plans for warn in plan.warnings]
        if warnings:
            print(f"\n⚠️  风险提示:")
            for code, warn in warnings[:3]:
                print(f"   [{code}] {warn}")
    
    def run(self):
        """运行监控循环"""
        print("\n" + "="*60)
        print("🚀 BIAS-ATR-Grid-Trader 实时监控系统启动")
        print("="*60)
        
        # 连接交易服务
        if self.conf.TRADE_CONFIG.AUTO_TRADE_ENABLED:
            if not self.trader.connect():
                print("⚠️ 交易服务连接失败，仅监控模式运行")
        
        # 自动同步持仓 (如果已连接交易服务)
        if getattr(self.conf, 'SYNC_HOLDINGS_ENABLED', False):
            if self.trader.is_connected():
                print("\n📊 正在同步持仓数据...")
                self.trader.sync_real_holdings()
            else:
                print("⚠️ 交易服务未连接，使用配置文件中的持仓数据")
        
        logger.info("监控系统启动", "Monitor")
        
        self._running = True
        loop_count = 0
        
        try:
            while self._running:
                loop_count += 1
                
                # 检查交易时间
                if not self._is_trading_time():
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"\r⏰ [{now}] 非交易时间，等待中... (按 Ctrl+C 退出)", end="")
                    time.sleep(30)
                    continue
                
                # 1. 分析策略 (每5分钟更新一次)
                if loop_count % 5 == 1:
                    print("\n📊 更新策略分析...")
                    plans = self.analyze_all()
                else:
                    plans = list(self.pending_orders.keys())
                    plans = [p for p in self.analyze_all() if p]
                
                # 2. 获取实时行情
                realtime_data = self.get_realtime_data(self.conf.ETF_LIST)
                
                # 3. 检查触发
                triggered = self.check_triggers(realtime_data)
                
                # 4. 显示状态
                if loop_count % 5 == 1 or triggered:
                    self.print_status(plans, realtime_data)
                else:
                    now = datetime.now().strftime("%H:%M:%S")
                    print(f"\r⏳ [{now}] 监控中... 触发:{len(triggered)} (按 Ctrl+C 退出)", end="")
                
                # 等待下一次刷新
                time.sleep(self.monitor_conf.REFRESH_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n🛑 监控已停止")
        finally:
            self._running = False
            self.trader.disconnect()
    
    def stop(self):
        """停止监控"""
        self._running = False


def main():
    """主入口"""
    monitor = GridMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
