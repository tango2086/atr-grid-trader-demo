# trader.py - 交易执行模块
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import config
from notifier import get_notifier

# 尝试导入 QMT 交易模块
try:
    if hasattr(config, 'QMT_PATH') and config.QMT_PATH:
        sys.path.insert(0, config.QMT_PATH)
    from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
    from xtquant.xttype import StockAccount
    from xtquant import xtconstant
    HAS_TRADER = True
except Exception as e:
    HAS_TRADER = False
    print(f"⚠️ XtTrader 加载失败: {e}")


@dataclass
class OrderResult:
    """下单结果"""
    success: bool
    order_id: int = 0
    message: str = ""
    code: str = ""
    direction: str = ""
    price: float = 0.0
    volume: int = 0


class TraderCallback(XtQuantTraderCallback if HAS_TRADER else object):
    """交易回调"""
    
    def on_stock_order(self, order):
        """报单回调"""
        notifier = get_notifier()
        status = "已报" if order.order_status == 50 else f"状态:{order.order_status}"
        print(f"📝 订单回调: {order.stock_code} {status}")
    
    def on_stock_trade(self, trade):
        """成交回调"""
        notifier = get_notifier()
        direction = "买入" if trade.order_type == xtconstant.STOCK_BUY else "卖出"
        notifier.trade_alert(
            trade.stock_code, 
            direction, 
            trade.traded_price, 
            trade.traded_volume,
            "SUCCESS"
        )
        print(f"✅ 成交: {trade.stock_code} {direction} {trade.traded_volume}股 @ {trade.traded_price}")
    
    def on_order_error(self, order_error):
        """下单失败回调"""
        notifier = get_notifier()
        notifier.error_alert(f"下单失败: {order_error.error_msg}")
        print(f"❌ 下单错误: {order_error.error_msg}")
    
    def on_cancel_error(self, cancel_error):
        """撤单失败回调"""
        print(f"❌ 撤单错误: {cancel_error.error_msg}")
    
    def on_order_stock_async_response(self, response):
        """异步下单回调"""
        if response.order_id > 0:
            print(f"📤 下单提交成功, 订单号: {response.order_id}")


class Trader:
    """交易执行器"""
    
    def __init__(self):
        self.conf = config.TRADE_CONFIG
        self.notifier = get_notifier()
        self.trader = None
        self.account = None
        self._connected = False
    
    def connect(self) -> bool:
        """连接交易服务"""
        if not HAS_TRADER:
            print("❌ XtTrader 未安装，无法进行交易")
            return False
        
        try:
            # 创建交易实例
            # path 为 MiniQMT 的 userdata_mini 路径
            path = config.QMT_PATH.replace("bin.x64", "userdata_mini")
            session_id = int(datetime.now().strftime("%H%M%S"))
            
            self.trader = XtQuantTrader(path, session_id)
            
            # 注册回调
            callback = TraderCallback()
            self.trader.register_callback(callback)
            
            # 启动交易线程
            self.trader.start()
            
            # 连接
            result = self.trader.connect()
            if result != 0:
                print(f"❌ 连接失败, 错误码: {result}")
                return False
            
            # 创建账户对象
            self.account = StockAccount(self.conf.ACCOUNT_ID)
            
            # 订阅账户信息
            self.trader.subscribe(self.account)
            
            self._connected = True
            print(f"✅ 交易服务连接成功, 账户: {self.conf.ACCOUNT_ID}")
            return True
            
        except Exception as e:
            self.notifier.error_alert("交易服务连接失败", e)
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.trader:
            self.trader.stop()
            self._connected = False
            print("🔌 交易服务已断开")
    
    def is_connected(self) -> bool:
        return self._connected
    
    def _convert_code(self, code: str) -> str:
        """转换代码格式: sh510050 -> 510050.SH"""
        return code[2:] + '.' + code[:2].upper()
    
    def get_positions(self) -> List[Dict]:
        """查询持仓"""
        if not self._connected:
            return []
        
        try:
            positions = self.trader.query_stock_positions(self.account)
            result = []
            for pos in positions:
                result.append({
                    'code': pos.stock_code,
                    'volume': pos.volume,
                    'available': pos.can_use_volume,
                    'avg_cost': pos.avg_price,
                    'market_value': pos.market_value
                })
            return result
        except Exception as e:
            self.notifier.error_alert("查询持仓失败", e)
            return []
    
    def _reverse_convert_code(self, symbol: str) -> str:
        """反向转换代码格式: 510050.SH -> sh510050"""
        parts = symbol.split('.')
        if len(parts) == 2:
            return parts[1].lower() + parts[0]
        return symbol
    
    def sync_real_holdings(self) -> bool:
        """
        同步真实持仓到 config.REAL_HOLDINGS
        
        Returns:
            是否同步成功
        """
        if not self._connected:
            print("⚠️ 交易服务未连接，无法同步持仓")
            return False
        
        try:
            positions = self.get_positions()
            synced_count = 0
            
            for pos in positions:
                # 转换代码格式: 510050.SH -> sh510050
                code = self._reverse_convert_code(pos['code'])
                
                # 检查是否在 ETF_LIST 中
                if code in config.ETF_LIST:
                    config.REAL_HOLDINGS[code] = {
                        'volume': pos['volume'],
                        'available': pos['available'],
                        'avg_cost': pos['avg_cost']
                    }
                    synced_count += 1
                    print(f"✅ 同步持仓: {code} = {pos['volume']}股 @ {pos['avg_cost']:.3f}")
            
            print(f"📊 持仓同步完成: {synced_count}/{len(config.ETF_LIST)} 只ETF")
            return True
            
        except Exception as e:
            self.notifier.error_alert("同步持仓失败", e)
            return False
    
    def get_balance(self) -> Dict:
        """查询资金"""
        if not self._connected:
            return {}
        
        try:
            assets = self.trader.query_stock_asset(self.account)
            if assets:
                return {
                    'total_asset': assets.total_asset,
                    'cash': assets.cash,
                    'frozen': assets.frozen_cash,
                    'market_value': assets.market_value
                }
            return {}
        except Exception as e:
            self.notifier.error_alert("查询资金失败", e)
            return {}
    
    def place_order(self, code: str, direction: str, price: float, volume: int, 
                    confirm: bool = True) -> OrderResult:
        """
        下单
        
        Args:
            code: 证券代码 (sh510050 格式)
            direction: BUY 或 SELL
            price: 委托价格
            volume: 委托数量
            confirm: 是否需要确认
        """
        result = OrderResult(success=False, code=code, direction=direction, 
                           price=price, volume=volume)
        
        # 检查是否允许自动下单
        if not self.conf.AUTO_TRADE_ENABLED:
            result.message = "自动下单已关闭"
            self.notifier.notify(
                "📋 下单请求 (仅提醒)",
                f"代码: {code}\n方向: {direction}\n价格: {price:.3f}\n数量: {volume}\n\n*自动下单已关闭，请手动操作*",
                "SIGNAL"
            )
            return result
        
        if not self._connected:
            result.message = "交易服务未连接"
            return result
        
        # 风控检查
        order_value = price * volume
        if order_value > self.conf.MAX_ORDER_VALUE:
            result.message = f"下单金额 {order_value:.0f} 超过限制 {self.conf.MAX_ORDER_VALUE}"
            self.notifier.error_alert(result.message)
            return result
        
        # 确认下单
        if confirm and self.conf.REQUIRE_CONFIRM:
            print(f"\n{'='*40}")
            print(f"⚠️ 下单确认")
            print(f"  代码: {code}")
            print(f"  方向: {direction}")
            print(f"  价格: {price:.3f}")
            print(f"  数量: {volume}")
            print(f"  金额: {order_value:.2f}")
            print(f"{'='*40}")
            
            user_input = input("确认下单? (y/n): ").strip().lower()
            if user_input != 'y':
                result.message = "用户取消"
                return result
        
        try:
            # 转换代码格式
            symbol = self._convert_code(code)
            
            # 确定买卖方向
            if direction == "BUY":
                order_type = xtconstant.STOCK_BUY
            else:
                order_type = xtconstant.STOCK_SELL
            
            # 下单
            order_id = self.trader.order_stock(
                self.account, 
                symbol, 
                order_type,
                volume,
                xtconstant.FIX_PRICE,  # 限价
                price
            )
            
            if order_id > 0:
                result.success = True
                result.order_id = order_id
                result.message = f"下单成功, 订单号: {order_id}"
                self.notifier.trade_alert(code, direction, price, volume, "已报")
            else:
                result.message = f"下单失败, 返回: {order_id}"
                self.notifier.error_alert(result.message)
                
        except Exception as e:
            result.message = str(e)
            self.notifier.error_alert("下单异常", e)
        
        return result
    
    def cancel_order(self, order_id: int) -> bool:
        """撤单"""
        if not self._connected:
            return False
        
        try:
            result = self.trader.cancel_order_stock(self.account, order_id)
            return result == 0
        except Exception as e:
            self.notifier.error_alert("撤单异常", e)
            return False


# 全局交易器实例
_trader = None

def get_trader() -> Trader:
    """获取全局交易器"""
    global _trader
    if _trader is None:
        _trader = Trader()
    return _trader


if __name__ == "__main__":
    # 测试
    trader = get_trader()
    
    print("尝试连接交易服务...")
    if trader.connect():
        print("\n查询持仓:")
        positions = trader.get_positions()
        for pos in positions:
            print(f"  {pos['code']}: {pos['volume']}股 @ {pos['avg_cost']:.3f}")
        
        print("\n查询资金:")
        balance = trader.get_balance()
        if balance:
            print(f"  总资产: {balance.get('total_asset', 0):.2f}")
            print(f"  可用资金: {balance.get('cash', 0):.2f}")
        
        trader.disconnect()
    else:
        print("连接失败，请检查 QMT 客户端是否运行")
