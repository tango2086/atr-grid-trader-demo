# persistence.py
import sqlite3
import os
from datetime import datetime
from logger import get_logger

logger = get_logger()

class GridStateManager:
    """网格状态持久化管理"""
    
    def __init__(self, db_path="grid_state.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 创建 today_grids 表
            # 记录: 日期, 代码, 价格, 方向 (避免同日同价位重复操作)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS triggered_grids (
                    date TEXT,
                    code TEXT,
                    price REAL,
                    direction TEXT,
                    timestamp TEXT,
                    PRIMARY KEY (date, code, price, direction)
                )
            ''')
            
            # 创建 grid_pairs 表 (网格配对)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS grid_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    buy_price REAL,
                    buy_amount INTEGER,
                    target_sell_price REAL,
                    status TEXT DEFAULT 'OPEN', -- OPEN, CLOSED
                    created_at TEXT,
                    closed_at TEXT
                )
            ''')

            # 创建 trade_history 表 (交易盈亏)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    direction TEXT,
                    price REAL,
                    volume INTEGER,
                    realized_pnl REAL DEFAULT 0,
                    timestamp TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}", "Persistence", exc=e)

    def is_grid_triggered(self, date: str, code: str, price: float, direction: str) -> bool:
        """
        检查某网格是否已触发
        精确匹配价格可能不准，建议使用近似匹配或确保输入价格一致
        这里假设价格由策略精确生成
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM triggered_grids WHERE date=? AND code=? AND ABS(price - ?) < 0.0001 AND direction=?', 
                           (date, code, price, direction))
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except Exception as e:
            logger.error(f"查询网格状态失败: {e}", "Persistence")
            return False

    def mark_grid_triggered(self, date: str, code: str, price: float, direction: str):
        """标记网格为已触发"""
        try:
            now_str = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO triggered_grids (date, code, price, direction, timestamp) VALUES (?, ?, ?, ?, ?)',
                           (date, code, price, direction, now_str))
            conn.commit()
            conn.close()
            logger.info(f"状态已保存: {code} {direction} @ {price}", "Persistence")
        except Exception as e:
            logger.error(f"保存网格状态失败: {e}", "Persistence", exc=e)

    # ---------------------------------------------------------
    # 网格配对管理 (Grid Pairing)
    # ---------------------------------------------------------
    def add_grid_pair(self, code: str, buy_price: float, buy_amount: int, target_sell_price: float):
        """记录新的网格配对 (买入后调用)"""
        try:
            now_str = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO grid_pairs (code, buy_price, buy_amount, target_sell_price, status, created_at)
                VALUES (?, ?, ?, ?, 'OPEN', ?)
            ''', (code, buy_price, buy_amount, target_sell_price, now_str))
            conn.commit()
            conn.close()
            logger.info(f"➕ 新增网格配对: {code} 买入@{buy_price:.3f} -> 目标@{target_sell_price:.3f}", "Persistence")
        except Exception as e:
            logger.error(f"新增网格配对失败: {e}", "Persistence", exc=e)

    def get_active_pairs(self, code: str):
        """获取指定ETF的所有未结清配对"""
        try:
            conn = sqlite3.connect(self.db_path)
            # 返回字典列表
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM grid_pairs WHERE code=? AND status='OPEN' ORDER BY buy_price DESC", (code,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"查询配对失败: {e}", "Persistence")
            return []

    def close_pair(self, pair_id: int):
        """结清网格配对 (卖出后调用)"""
        try:
            now_str = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE grid_pairs SET status='CLOSED', closed_at=? WHERE id=?", (now_str, pair_id))
            conn.commit()
            conn.close()
            logger.info(f"✅ 结清网格配对 ID: {pair_id}", "Persistence")
        except Exception as e:
            logger.error(f"结清配对失败: {e}", "Persistence", exc=e)

    # ---------------------------------------------------------
    # 交易历史与盈亏 (Trade History & PnL)
    # ---------------------------------------------------------
    def add_trade_record(self, code: str, direction: str, price: float, volume: int, realized_pnl: float = 0):
        """记录交易及盈亏"""
        try:
            now_str = datetime.now().isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trade_history (code, direction, price, volume, realized_pnl, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (code, direction, price, volume, realized_pnl, now_str))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"记录交易历史失败: {e}", "Persistence", exc=e)

    def get_realized_pnl(self, start_date: str = None):
        """获取已实现盈亏总和"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            sql = "SELECT SUM(realized_pnl) FROM trade_history"
            args = []
            if start_date:
                # 支持两种格式：YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SS
                if len(start_date) == 10:  # YYYY-MM-DD
                    sql += " WHERE date(timestamp) >= ?"
                else:  # ISO format
                    sql += " WHERE timestamp >= ?"
                args.append(start_date)

            cursor.execute(sql, tuple(args))
            result = cursor.fetchone()[0]
            conn.close()
            return float(result) if result else 0.0
        except Exception as e:
            logger.error(f"查询盈亏失败: {e}", "Persistence")
            return 0.0

    def clear_old_records(self, days_to_keep=7):
        """清理旧记录"""
        try:
            # 简单实现，暂不清理，仅作为预留接口
            pass
        except Exception as e:
            pass

# 单例模式
grid_state_manager = GridStateManager()
