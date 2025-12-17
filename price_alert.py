# price_alert.py - 价格提醒功能
"""
价格提醒系统：
- 检测价格是否触及网格买卖价位
- 管理提醒历史记录
- 提供提醒查询接口
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Set
import json
import os

@dataclass
class PriceAlert:
    """价格提醒记录"""
    id: str
    code: str
    name: str
    alert_type: str  # 'BUY_TOUCH', 'SELL_TOUCH'
    price: float
    target_price: float
    direction: str  # 'BUY', 'SELL'
    grid_level: int  # 网格层级：买1=1, 卖1=1, 买2=2, 卖2=2
    timestamp: datetime
    message: str
    amount: int = 0  # 订单数量

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'alert_type': self.alert_type,
            'price': self.price,
            'target_price': self.target_price,
            'direction': self.direction,
            'grid_level': self.grid_level,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message,
            'amount': self.amount
        }

class AlertManager:
    """价格提醒管理器"""

    def __init__(self, data_file='data/alerts.json'):
        self.data_file = data_file
        self.alerts: List[PriceAlert] = []
        self.alerted_prices: Dict[str, Set[str]] = {}  # 记录已经提醒过的价格，避免重复提醒
        self._load_alerts()
        self._cleanup_old_alerts()

    def _load_alerts(self):
        """加载历史提醒记录"""
        try:
            if os.path.exists(self.data_file):
                os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.alerts = []
                    for alert_data in data.get('alerts', []):
                        alert_data['timestamp'] = datetime.fromisoformat(alert_data['timestamp'])
                        self.alerts.append(PriceAlert(**alert_data))
        except Exception as e:
            print(f"加载提醒记录失败: {e}")
            self.alerts = []

    def _save_alerts(self):
        """保存提醒记录"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            data = {
                'alerts': [alert.to_dict() for alert in self.alerts],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存提醒记录失败: {e}")

    def _cleanup_old_alerts(self):
        """清理过期的提醒记录（保留7天）"""
        cutoff_date = datetime.now() - timedelta(days=7)
        self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_date]

        # 清理过期的价格提醒记录（保留1天）
        today = datetime.now().date()
        if hasattr(self, 'alerted_prices'):
            keys_to_remove = []
            for key in self.alerted_prices:
                try:
                    alert_date = datetime.strptime(key.split('_')[0], '%Y-%m-%d').date()
                    if alert_date < today:
                        keys_to_remove.append(key)
                except:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self.alerted_prices[key]

    def generate_alert_id(self) -> str:
        """生成唯一提醒ID"""
        return f"alert_{int(datetime.now().timestamp() * 1000)}"

    def check_price_alerts(self, code: str, name: str, current_price: float,
                          suggested_orders: List[Dict]) -> List[PriceAlert]:
        """检测价格提醒"""
        new_alerts = []
        today_key = datetime.now().strftime('%Y-%m-%d')

        # 初始化今天的提醒记录
        if today_key not in self.alerted_prices:
            self.alerted_prices[today_key] = set()

        today_alerted = self.alerted_prices[today_key]

        for order in suggested_orders:
            direction = order.get('direction')
            target_price = order.get('price', 0)
            desc = order.get('desc', '')
            amount = order.get('amount', 0)  # 获取订单数量

            if not target_price or target_price <= 0:
                continue

            # 检测是否触及买价（当前价格 <= 目标买价）
            if direction == 'BUY' and current_price <= target_price:
                alert_key = f"{code}_BUY_{target_price:.3f}"
                if alert_key not in today_alerted:
                    # 提取网格层级
                    grid_level = 1
                    if '买2' in desc:
                        grid_level = 2
                    elif '买3' in desc:
                        grid_level = 3

                    alert = PriceAlert(
                        id=self.generate_alert_id(),
                        code=code,
                        name=name,
                        alert_type='BUY_TOUCH',
                        price=current_price,
                        target_price=target_price,
                        direction='BUY',
                        grid_level=grid_level,
                        timestamp=datetime.now(),
                        message=f"🔥 {name} 触及买{grid_level}价位！当前价: {current_price:.3f}, 目标价: {target_price:.3f}",
                        amount=amount  # 添加订单数量
                    )

                    new_alerts.append(alert)
                    self.alerts.append(alert)
                    today_alerted.add(alert_key)

            # 检测是否触及卖价（当前价格 >= 目标卖价）
            elif direction == 'SELL' and current_price >= target_price:
                alert_key = f"{code}_SELL_{target_price:.3f}"
                if alert_key not in today_alerted:
                    # 提取网格层级
                    grid_level = 1
                    if '卖2' in desc:
                        grid_level = 2
                    elif '卖3' in desc:
                        grid_level = 3

                    alert = PriceAlert(
                        id=self.generate_alert_id(),
                        code=code,
                        name=name,
                        alert_type='SELL_TOUCH',
                        price=current_price,
                        target_price=target_price,
                        direction='SELL',
                        grid_level=grid_level,
                        timestamp=datetime.now(),
                        message=f"💰 {name} 触及卖{grid_level}价位！当前价: {current_price:.3f}, 目标价: {target_price:.3f}",
                        amount=amount  # 添加订单数量
                    )

                    new_alerts.append(alert)
                    self.alerts.append(alert)
                    today_alerted.add(alert_key)

        # 保存更新
        if new_alerts:
            self._save_alerts()

        return new_alerts

    def get_recent_alerts(self, hours: int = 24) -> List[PriceAlert]:
        """获取最近的提醒记录"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alerts if alert.timestamp > cutoff_time]

    def get_alerts_by_code(self, code: str, hours: int = 24) -> List[PriceAlert]:
        """获取指定ETF的提醒记录"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alerts
                if alert.code == code and alert.timestamp > cutoff_time]

    def get_alert_count(self, hours: int = 24) -> Dict[str, int]:
        """获取提醒统计"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]

        stats = {
            'total': len(recent_alerts),
            'buy_touch': len([a for a in recent_alerts if a.alert_type == 'BUY_TOUCH']),
            'sell_touch': len([a for a in recent_alerts if a.alert_type == 'SELL_TOUCH'])
        }

        # 按ETF统计
        by_etf = {}
        for alert in recent_alerts:
            if alert.code not in by_etf:
                by_etf[alert.code] = 0
            by_etf[alert.code] += 1

        stats['by_etf'] = by_etf
        return stats

    def clear_old_alerts(self, days: int = 7):
        """手动清理旧提醒记录"""
        cutoff_date = datetime.now() - timedelta(days=days)
        old_count = len(self.alerts)
        self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_date]
        new_count = len(self.alerts)

        self._save_alerts()
        return old_count - new_count

# 全局提醒管理器实例
alert_manager = AlertManager()