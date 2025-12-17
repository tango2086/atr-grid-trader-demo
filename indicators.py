# indicators.py
import pandas as pd
import numpy as np

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算策略所需的核心指标: MA_5, MA_20, BIAS_20, ATR_14

    Args:
        df: 包含 'open', 'high', 'low', 'close' 列的 DataFrame

    Returns:
        添加了 'ma_5', 'ma_20', 'bias_20', 'atr_14' 列的 DataFrame
    """
    # 确保数据按时间升序排列
    df = df.sort_index()

    # 1. 计算 MA_5 (用于网格基准价锚定)
    df['ma_5'] = df['close'].rolling(window=5).mean()

    # 2. 计算 MA_20
    df['ma_20'] = df['close'].rolling(window=20).mean()
    
    # 3. 计算 BIAS_20
    # BIAS = (收盘价 - 均线) / 均线 * 100
    # 注意: 防止除以0 (虽然均线一般不为0)
    df['bias_20'] = (df['close'] - df['ma_20']) / df['ma_20'] * 100
    
    # 4. 计算 ATR_14
    # TR = Max(High-Low, Abs(High-PreClose), Abs(Low-PreClose))
    high = df['high']
    low = df['low']
    close = df['close']
    pre_close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - pre_close).abs()
    tr3 = (low - pre_close).abs()
    
    # TR 取三者最大值
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR 一般使用 Wilder's Smoothing (RM = Rolling Mean for simplicity here or ewm)
    # 标准定义常用 SMA(TR, 14) 或者 RMA(TR, 14)。这里使用简单移动平均 SMA，足够稳健。
    df['atr_14'] = df['tr'].rolling(window=14).mean()
    
    # 清理中间变量
    df.drop(columns=['tr'], inplace=True)
    
    # 5. 计算 RSI_14
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    # 处理除以0的情况 (loss为0)
    df['rsi_14'] = df['rsi_14'].fillna(100)
    
    # 6. 计算 KDJ (9,3,3)
    # RSV = (Close - MinLow_9) / (MaxHigh_9 - MinLow_9) * 100
    low_9 = low.rolling(window=9).min()
    high_9 = high.rolling(window=9).max()
    rsv = (close - low_9) / (high_9 - low_9) * 100
    # K = 2/3*PrevK + 1/3*RSV
    # D = 2/3*PrevD + 1/3*K
    # J = 3*K - 2*D
    # Pandas ewm adjust=False mimics the recurrence relation nicely
    df['kdj_k'] = rsv.ewm(com=2, adjust=False).mean()
    df['kdj_d'] = df['kdj_k'].ewm(com=2, adjust=False).mean()
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
    
    return df