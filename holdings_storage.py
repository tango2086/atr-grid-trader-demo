# holdings_storage.py - 本地持仓存储模块
"""
本地 JSON 存储持仓数据：
- 支持手动下单后自动更新持仓
- 数据持久化到本地文件
- 启动时自动加载
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional

# 持仓数据文件路径
HOLDINGS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'holdings.json')


def _ensure_data_dir():
    """确保 data 目录存在"""
    data_dir = os.path.dirname(HOLDINGS_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)


def load_holdings() -> Dict:
    """
    从本地文件加载持仓数据
    
    Returns:
        持仓字典 {code: {volume, avg_cost, available}}
    """
    _ensure_data_dir()
    
    if os.path.exists(HOLDINGS_FILE):
        try:
            with open(HOLDINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[DATA] 已加载本地持仓数据: {len(data.get('holdings', {}))} 只ETF")
                return data.get('holdings', {})
        except Exception as e:
            print(f"[WARN] 加载持仓数据失败: {e}")
    
    return {}


def save_holdings(holdings: Dict) -> bool:
    """
    保存持仓数据到本地文件
    
    Args:
        holdings: 持仓字典
        
    Returns:
        是否保存成功
    """
    _ensure_data_dir()
    
    try:
        data = {
            'holdings': holdings,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(HOLDINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[SAVE] 持仓数据已保存")
        return True
    except Exception as e:
        print(f"⚠️ 保存持仓数据失败: {e}")
        return False


def update_holding_after_trade(code: str, direction: str, price: float, volume: int) -> Dict:
    """
    下单后更新持仓数据
    
    Args:
        code: ETF 代码 (如 sh512760)
        direction: BUY 或 SELL
        price: 成交价格
        volume: 成交数量
        
    Returns:
        更新后的持仓数据
    """
    import config
    
    # 获取当前持仓
    current = config.REAL_HOLDINGS.get(code, {
        'volume': 0,
        'avg_cost': 0,
        'available': 0
    })
    
    old_volume = current.get('volume', 0)
    old_cost = current.get('avg_cost', 0)
    
    if direction == 'BUY':
        # 买入: 计算新的平均成本
        new_volume = old_volume + volume
        if new_volume > 0:
            # 加权平均成本
            total_cost = old_volume * old_cost + volume * price
            new_cost = total_cost / new_volume
        else:
            new_cost = price
        
        new_holding = {
            'volume': new_volume,
            'avg_cost': round(new_cost, 4),
            'available': current.get('available', 0)  # 买入当天不可卖
        }
    else:  # SELL
        # 卖出: 减少持仓，成本不变
        new_volume = max(0, old_volume - volume)
        new_available = max(0, current.get('available', 0) - volume)
        
        new_holding = {
            'volume': new_volume,
            'avg_cost': old_cost if new_volume > 0 else 0,
            'available': new_available
        }
    
    # 更新 config
    config.REAL_HOLDINGS[code] = new_holding
    
    # 保存到本地
    save_holdings(config.REAL_HOLDINGS)
    
    print(f"[UPDATE] 持仓已更新: {code} = {new_holding['volume']}股 @ ¥{new_holding['avg_cost']:.3f}")
    
    return new_holding


def init_holdings_from_local():
    """
    启动时从本地文件初始化持仓数据到 config.REAL_HOLDINGS
    """
    import config
    
    local_holdings = load_holdings()
    
    if local_holdings:
        # 用本地数据覆盖 config 中的默认值
        for code, holding in local_holdings.items():
            config.REAL_HOLDINGS[code] = holding
        print(f"[LOAD] 已从本地文件加载 {len(local_holdings)} 只ETF持仓")
    else:
        # 如果本地没有数据，将 config 中的默认值保存到本地
        if config.REAL_HOLDINGS:
            save_holdings(config.REAL_HOLDINGS)
            print(f"📝 已将默认持仓保存到本地文件")
