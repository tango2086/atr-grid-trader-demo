# logger.py - 统一日志系统
"""
提供交易系统的日志记录功能：
- 分日期存储日志文件
- 支持控制台和文件双输出
- 按级别分类日志
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class TradingLogger:
    """交易日志管理器"""
    
    _instance: Optional['TradingLogger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 创建主日志器
        self.logger = logging.getLogger("BIAS-ATR-Trader")
        self.logger.setLevel(logging.DEBUG)
        
        # 清除已有handler (避免重复)
        self.logger.handlers.clear()
        
        # 今日日志文件
        today = datetime.now().strftime("%Y%m%d")
        log_file = self.log_dir / f"trading_{today}.log"
        
        # 文件 Handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台 Handler (仅 WARNING 及以上)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            '%(levelname)s | %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 写入启动日志
        self.logger.info("=" * 60)
        self.logger.info("交易系统日志启动")
        self.logger.info("=" * 60)
        
        # [NEW] 内存日志缓存 (用于Web展示)
        from collections import deque
        self.log_buffer = deque(maxlen=200)
        
        # 自定义 Handler 用于捕获日志到 deque
        class MemoryListHandler(logging.Handler):
            def __init__(self, buffer):
                super().__init__()
                self.buffer = buffer
                
            def emit(self, record):
                msg = self.format(record)
                # 简单存储字典
                self.buffer.append({
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'level': record.levelname,
                    'message': record.getMessage() # 不含时间前缀
                })
        
        mem_handler = MemoryListHandler(self.log_buffer)
        mem_handler.setLevel(logging.INFO)
        self.logger.addHandler(mem_handler)

    def get_recent_logs(self, limit=50):
        """获取最近日志"""
        return list(self.log_buffer)[-limit:]
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """获取子日志器"""
        if name:
            return self.logger.getChild(name)
        return self.logger
    
    # 便捷方法
    def info(self, message: str, module: str = "System"):
        self.logger.info(f"[{module}] {message}")
    
    def warning(self, message: str, module: str = "System"):
        self.logger.warning(f"[{module}] {message}")
    
    def error(self, message: str, module: str = "System", exc: Exception = None):
        if exc:
            self.logger.error(f"[{module}] {message}: {exc}", exc_info=True)
        else:
            self.logger.error(f"[{module}] {message}")
    
    def debug(self, message: str, module: str = "System"):
        self.logger.debug(f"[{module}] {message}")
    
    # 交易专用日志
    def log_signal(self, code: str, direction: str, price: float, reason: str):
        """记录交易信号"""
        self.logger.info(
            f"[信号] {code} | {direction} | 价格:{price:.3f} | {reason}"
        )
    
    def log_order(self, code: str, direction: str, price: float, volume: int, status: str):
        """记录订单"""
        self.logger.info(
            f"[订单] {code} | {direction} | {volume}股 @ {price:.3f} | {status}"
        )
    
    def log_trade(self, code: str, direction: str, price: float, volume: int, profit: float = None):
        """记录成交"""
        profit_str = f" | 盈亏:{profit:+.2f}" if profit else ""
        self.logger.info(
            f"[成交] {code} | {direction} | {volume}股 @ {price:.3f}{profit_str}"
        )
    
    def log_risk(self, code: str, risk_type: str, message: str):
        """记录风控事件"""
        self.logger.warning(
            f"[风控] {code} | 类型:{risk_type} | {message}"
        )


# 全局日志器
_trading_logger: Optional[TradingLogger] = None


def get_logger() -> TradingLogger:
    """获取全局日志器"""
    global _trading_logger
    if _trading_logger is None:
        _trading_logger = TradingLogger()
    return _trading_logger


def setup_logger() -> logging.Logger:
    """初始化并返回 Python 标准日志器 (兼容旧接口)"""
    return get_logger().get_logger()


if __name__ == "__main__":
    # 测试
    logger = get_logger()
    logger.info("这是一条信息日志", "Test")
    logger.warning("这是一条警告日志", "Test")
    logger.log_signal("sh510050", "BUY", 3.456, "触及网格买入价")
    logger.log_order("sh510050", "BUY", 3.450, 200, "已报")
    logger.log_risk("sh510050", "逃顶", "BIAS > 20%, 触发逃顶规则")
    
    print(f"\n日志已保存到: logs/trading_{datetime.now():%Y%m%d}.log")
