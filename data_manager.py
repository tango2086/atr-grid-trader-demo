# data_manager.py - 统一数据管理模块
"""
统一管理数据获取逻辑：
- 优先使用 QMT 数据源
- QMT 不可用时使用 mootdx (通达信)
- 最后 fallback 到 Mock 数据
- 数据缓存机制
"""

import sys
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import config

# ============================================
# 数据源状态
# ============================================
HAS_XTDATA = False
HAS_MOOTDX = False
xtdata = None

# 1. 尝试导入 QMT 数据模块
try:
    if hasattr(config, 'QMT_PATH') and config.QMT_PATH:
        sys.path.insert(0, config.QMT_PATH)
    from xtquant import xtdata as _xtdata
    _xtdata.connect()
    xtdata = _xtdata
    HAS_XTDATA = True
    print("[OK] QMT 数据源已连接")
except Exception as e:
    print(f"[WARN] QMT 数据服务未连接: {e}")

# 2. 尝试导入 mootdx 数据模块
try:
    from mootdx.quotes import Quotes
    HAS_MOOTDX = True
    print("[OK] Mootdx 数据源可用")
except ImportError:
    print("[WARN] Mootdx 未安装 (pip install mootdx)")
except Exception as e:
    print(f"[WARN] Mootdx 初始化失败: {e}")


class DataManager:
    """统一数据管理器"""
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 缓存5分钟
        self._mootdx_client = None
        
        # 初始化 mootdx 客户端
        if HAS_MOOTDX:
            try:
                self._mootdx_client = Quotes.factory(market='std')
            except Exception as e:
                print(f"Mootdx 客户端初始化失败: {e}")
    
    @staticmethod
    def convert_code(code: str) -> str:
        """转换代码格式: sh510050 -> 510050.SH"""
        return code[2:] + '.' + code[:2].upper()
    
    @staticmethod
    def reverse_convert_code(symbol: str) -> str:
        """反向转换代码格式: 510050.SH -> sh510050"""
        parts = symbol.split('.')
        if len(parts) == 2:
            return parts[1].lower() + parts[0]
        return symbol
    
    @staticmethod
    def get_mootdx_market(code: str) -> int:
        """获取 mootdx 市场代码: sh -> 1, sz -> 0"""
        return 1 if code.startswith('sh') else 0
    
    @staticmethod
    def get_mootdx_symbol(code: str) -> str:
        """获取 mootdx 股票代码: sh510050 -> 510050"""
        return code[2:]
    
    def _is_cache_valid(self, code: str) -> bool:
        """检查缓存是否有效"""
        if code not in self._cache:
            return False
        cache_time = self._cache_time.get(code)
        if not cache_time:
            return False
        return (datetime.now() - cache_time).total_seconds() < self._cache_ttl
    
    def get_history(self, code: str, count: int = 200, use_cache: bool = True) -> pd.DataFrame:
        """
        获取历史数据
        
        优先级: QMT -> mootdx -> Mock
        
        Args:
            code: ETF代码 (sh510050 格式)
            count: 获取的数据条数
            use_cache: 是否使用缓存
        
        Returns:
            包含 OHLCV 数据的 DataFrame
        """
        # 检查缓存
        if use_cache and self._is_cache_valid(code):
            return self._cache[code].tail(count)
        
        df = None
        
        # 1. 尝试 QMT 数据源
        if HAS_XTDATA and xtdata:
            df = self._get_from_qmt(code, count)
        
        # 2. 尝试 mootdx 数据源
        if (df is None or df.empty) and HAS_MOOTDX and self._mootdx_client:
            df = self._get_from_mootdx(code, count)
        
        # 3. Fallback: Mock 数据
        if df is None or df.empty:
            df = self._generate_mock_data(code, count)
        
        # 更新缓存
        self._cache[code] = df
        self._cache_time[code] = datetime.now()
        
        return df
    
    def _get_from_qmt(self, code: str, count: int) -> Optional[pd.DataFrame]:
        """从 QMT 获取数据"""
        try:
            symbol = self.convert_code(code)
            
            # 下载历史数据
            xtdata.download_history_data(symbol, period='1d', incrementally=True)
            
            # 使用 get_market_data_ex 获取数据
            data = xtdata.get_market_data_ex(
                field_list=[],
                stock_list=[symbol],
                period='1d',
                count=count
            )
            
            if data and symbol in data:
                df = data[symbol]
                if df is not None and not df.empty and 'close' in df.columns:
                    df.index.name = 'date'
                    print(f"[{code}] QMT 数据: {len(df)} 条")
                    return df
        except Exception as e:
            print(f"[{code}] QMT 获取失败: {e}")
        
        return None
    
    def _get_from_mootdx(self, code: str, count: int) -> Optional[pd.DataFrame]:
        """从 mootdx (通达信) 获取数据"""
        try:
            market = self.get_mootdx_market(code)
            symbol = self.get_mootdx_symbol(code)
            
            # 获取日K线数据
            df = self._mootdx_client.bars(
                symbol=symbol,
                frequency=9,  # 9=日K线
                market=market,
                offset=count
            )
            
            if df is not None and not df.empty:
                # 标准化列名
                df = df.rename(columns={
                    'open': 'open',
                    'high': 'high', 
                    'low': 'low',
                    'close': 'close',
                    'vol': 'volume',
                    'amount': 'amount'
                })
                
                # 确保有必要的列
                if 'close' in df.columns:
                    # 设置日期索引
                    if 'datetime' in df.columns:
                        df['date'] = pd.to_datetime(df['datetime'])
                        df.set_index('date', inplace=True)
                    df.index.name = 'date'
                    
                    print(f"[{code}] Mootdx 数据: {len(df)} 条")
                    return df
        except Exception as e:
            print(f"[{code}] Mootdx 获取失败: {e}")
        
        return None
    
    def get_realtime(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时行情
        
        Args:
            codes: ETF代码列表 (sh510050 格式)
        
        Returns:
            {code: {'price': float, 'open': float, ...}}
        """
        result = {}
        
        # 1. 尝试 QMT 实时行情
        if HAS_XTDATA and xtdata:
            try:
                symbols = [self.convert_code(code) for code in codes]
                data = xtdata.get_full_tick(symbols)
                
                for code, symbol in zip(codes, symbols):
                    if symbol in data and data[symbol]:
                        tick = data[symbol]
                        result[code] = {
                            'price': tick.get('lastPrice', 0),
                            'open': tick.get('open', 0),
                            'high': tick.get('high', 0),
                            'low': tick.get('low', 0),
                            'volume': tick.get('volume', 0),
                            'time': tick.get('time', 0)
                        }
                
                if result:
                    return result
            except Exception as e:
                print(f"QMT 实时行情失败: {e}")
        
        # 2. 尝试 mootdx 实时行情
        if HAS_MOOTDX and self._mootdx_client:
            try:
                for code in codes:
                    market = self.get_mootdx_market(code)
                    symbol = self.get_mootdx_symbol(code)
                    
                    # 获取最新K线作为实时价格
                    df = self._mootdx_client.bars(
                        symbol=symbol,
                        frequency=9,
                        market=market,
                        offset=1
                    )
                    
                    if df is not None and not df.empty:
                        last = df.iloc[-1]
                        result[code] = {
                            'price': last.get('close', 0),
                            'open': last.get('open', 0),
                            'high': last.get('high', 0),
                            'low': last.get('low', 0),
                            'volume': last.get('vol', 0),
                            'time': datetime.now().strftime('%H%M%S')
                        }
                
                if result:
                    return result
            except Exception as e:
                print(f"Mootdx 实时行情失败: {e}")
        
        # 3. Fallback: 使用历史数据
        for code in codes:
            if code not in result:
                df = self.get_history(code, count=1, use_cache=True)
                if not df.empty:
                    last = df.iloc[-1]
                    result[code] = {
                        'price': last['close'],
                        'open': last.get('open', last['close']),
                        'high': last.get('high', last['close']),
                        'low': last.get('low', last['close']),
                        'volume': last.get('volume', 0),
                        'time': datetime.now().strftime('%H%M%S')
                    }
        
        return result
    
    def _generate_mock_data(self, code: str, count: int = 100) -> pd.DataFrame:
        """生成模拟数据"""
        print(f"[{code}] 使用模拟数据...")
        
        dates = pd.date_range(end=datetime.now(), periods=count)
        base_price = 3.0
        
        data = []
        for i in range(count):
            noise = random.uniform(-0.02, 0.02)
            trend = math.sin(i / 10.0) * 0.5
            price = base_price * (1 + trend + noise)
            high = price * (1 + random.uniform(0, 0.01))
            low = price * (1 - random.uniform(0, 0.01))
            
            data.append({
                'open': price * (1 - random.uniform(-0.005, 0.005)),
                'high': high,
                'low': low,
                'close': price,
                'volume': random.randint(500000, 2000000)
            })
        
        df = pd.DataFrame(data, index=dates)
        df.index.name = 'date'
        return df
    
    def clear_cache(self, code: Optional[str] = None):
        """清除缓存"""
        if code:
            self._cache.pop(code, None)
            self._cache_time.pop(code, None)
        else:
            self._cache.clear()
            self._cache_time.clear()
    
    def is_connected(self) -> bool:
        """检查是否连接到真实数据源"""
        return HAS_XTDATA or HAS_MOOTDX
    
    def get_data_source(self) -> str:
        """获取当前使用的数据源名称"""
        if HAS_XTDATA:
            return "QMT"
        elif HAS_MOOTDX:
            return "Mootdx"
        else:
            return "Mock"


# 全局数据管理器实例
_data_manager: Optional[DataManager] = None


def get_data_manager() -> DataManager:
    """获取全局数据管理器"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager


# 便捷函数 (兼容旧接口)
def get_data(code: str) -> pd.DataFrame:
    """获取历史数据 (兼容旧接口)"""
    return get_data_manager().get_history(code)


if __name__ == "__main__":
    # 测试
    dm = get_data_manager()
    print(f"\n数据源: {dm.get_data_source()}")
    print(f"QMT: {'✅' if HAS_XTDATA else '❌'} | Mootdx: {'✅' if HAS_MOOTDX else '❌'}")
    
    # 测试获取数据
    print("\n测试数据获取:")
    for code in config.ETF_LIST[:2]:
        df = dm.get_history(code, count=50)
        if not df.empty:
            print(f"  {code}: {len(df)} 条, 最新价 {df['close'].iloc[-1]:.3f}")
