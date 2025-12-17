# notifier.py - 通知推送模块
import json
from datetime import datetime
from typing import Optional
import config

# 尝试导入 requests
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️ requests 未安装，微信通知不可用")


class Notifier:
    """统一通知管理器"""
    
    def __init__(self):
        self.conf = config.NOTIFY_CONFIG
        self._last_notify_time = {}  # 防止重复通知
    
    def notify(self, title: str, content: str, level: str = "INFO"):
        """
        发送通知
        
        Args:
            title: 通知标题
            content: 通知内容
            level: 级别 INFO/WARNING/ERROR/TRADE
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 1. 控制台通知 (始终输出)
        if self.conf.CONSOLE_ENABLED:
            self._console_notify(title, content, level, timestamp)
        
        # 2. PushPlus 微信通知
        if self.conf.PUSHPLUS_ENABLED and HAS_REQUESTS:
            self._pushplus_notify(title, content)
    
    def _console_notify(self, title: str, content: str, level: str, timestamp: str):
        """控制台通知"""
        icons = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "TRADE": "💰",
            "SIGNAL": "📊"
        }
        icon = icons.get(level, "📢")
        
        print(f"\n{'='*50}")
        print(f"{icon} [{timestamp}] {title}")
        print(f"{'='*50}")
        print(content)
        print()
    
    def _pushplus_notify(self, title: str, content: str):
        """PushPlus 微信通知"""
        token = self.conf.PUSHPLUS_TOKEN
        if not token:
            return
        
        url = "http://www.pushplus.plus/send"
        data = {
            "token": token,
            "title": title,
            "content": content,
            "template": "markdown"  # 使用 markdown 模板
        }
        
        # 如果配置了群组
        topic = getattr(self.conf, 'PUSHPLUS_TOPIC', '')
        if topic:
            data["topic"] = topic
        
        try:
            resp = requests.post(url, json=data, timeout=5)
            result = resp.json()
            if result.get("code") != 200:
                print(f"PushPlus 通知失败: {result.get('msg')}")
        except Exception as e:
            print(f"PushPlus 通知异常: {e}")
    
    # ========== 便捷方法 ==========
    
    def signal_alert(self, code: str, signal_type: str, price: float, reason: str):
        """信号提醒"""
        if not self.conf.NOTIFY_ON_SIGNAL:
            return
        
        emoji = "🟢" if signal_type == "BUY" else "🔴"
        title = f"{emoji} {code} {signal_type}信号"
        content = f"""
- **代码**: {code}
- **方向**: {signal_type}
- **价格**: ¥{price:.3f}
- **原因**: {reason}
"""
        self.notify(title, content, "SIGNAL")
    
    def trade_alert(self, code: str, direction: str, price: float, volume: int, status: str):
        """交易提醒"""
        if not self.conf.NOTIFY_ON_TRADE:
            return
        
        emoji = "✅" if status == "SUCCESS" else "❌"
        title = f"{emoji} {code} {direction}单 {status}"
        content = f"""
- **代码**: {code}
- **方向**: {direction}
- **价格**: ¥{price:.3f}
- **数量**: {volume}股
- **状态**: {status}
"""
        self.notify(title, content, "TRADE")
    
    def error_alert(self, message: str, exception: Optional[Exception] = None):
        """错误提醒"""
        if not self.conf.NOTIFY_ON_ERROR:
            return
        
        content = f"**错误信息**: {message}"
        if exception:
            content += f"\n**异常详情**: {str(exception)}"
        
        self.notify("⚠️ 系统错误", content, "ERROR")
    
    def market_summary(self, summary_data: dict):
        """市场概览"""
        title = "📊 市场状态更新"
        content = "| 代码 | 价格 | BIAS | 状态 |\n|---|---|---|---|\n"
        
        for item in summary_data.get("items", []):
            content += f"| {item['code']} | {item['price']:.3f} | {item['bias']:.1f}% | {item['status']} |\n"
        
        self.notify(title, content, "INFO")


# 全局通知器实例
_notifier = None

def get_notifier() -> Notifier:
    """获取全局通知器"""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier


if __name__ == "__main__":
    # 测试
    notifier = get_notifier()
    notifier.notify("测试通知", "这是一条测试消息", "INFO")
    notifier.signal_alert("sh510050", "BUY", 3.456, "触及网格买入价")
