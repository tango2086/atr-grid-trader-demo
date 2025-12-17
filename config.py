# config.py
# BIAS-ATR-Grid-Trader 策略配置文件

# 0. 数据源配置
# 数据源选择: 'akshare' (推荐, 免费), 'tushare' (需要token), 'qmt' (仅行情)
DATA_SOURCE = 'akshare'

# Tushare配置 (如果使用tushare)
TUSHARE_TOKEN = ''  # 从 https://tushare.pro 获取token

# 国金QMT配置
QMT_PATH = r"D:\国金QMT交易端模拟\bin.x64"  # QMT 路径
SYNC_HOLDINGS_ENABLED = False  # 是否从 QMT 自动同步持仓 (需交易服务连接)

# 数据源配置参数
DATA_CONFIG = {
    'cache_enabled': True,      # 启用数据缓存
    'cache_duration': 60,       # 缓存时长(秒)
    'retry_times': 3,          # 请求失败重试次数
    'timeout': 10,             # 请求超时时间(秒)
}

# 1. ETF 池 (用户真实持仓)
# 格式: "sh510300" 或 "sz159915"
ETF_LIST = [
    "sh510050",  # 上证50ETF
    "sh588090",  # 科创ETF
    "sz159841",  # 证券ETF
    "sh512480",  # 半导体ETF
    "sh512760",  # 芯片ETF
]

# ETF 名称映射
ETF_NAMES = {
    "sh510050": "上证50",
    "sh588090": "科创50",
    "sz159841": "证券ETF",
    "sh512480": "半导体",
    "sh512760": "芯片ETF",
}

# 用户真实持仓信息 (代码: {股数, 成本价, 可用股数})
REAL_HOLDINGS = {
    "sh510050": {"volume": 6400, "avg_cost": 3.10, "available": 6400},
    "sh588090": {"volume": 18000, "avg_cost": 1.11, "available": 18000},
    "sz159841": {"volume": 17200, "avg_cost": 1.17, "available": 17200},
    "sh512480": {"volume": 23000, "avg_cost": 1.43, "available": 23000},
    "sh512760": {"volume": 29000, "avg_cost": 1.76, "available": 29000},
}

# 2. 资金分配
TOTAL_CAPITAL = 200000.0  # 总资金: 20万
ETF_COUNT = 5             # ETF数量
CAPITAL_PER_ETF = TOTAL_CAPITAL / ETF_COUNT  # 单只ETF资金: 4万

# 3. BIAS 阈值 (BIAS_20) - 基于历史数据优化
# 区间定义:
#   深坑区: < DEEP_DIP           (激进买入)
#   黄金区: DEEP_DIP ~ GOLD_ZONE_UPPER  (建议买入)
#   震荡区: GOLD_ZONE_UPPER ~ OSCILLATION_UPPER  (网格交易)
#   减持区: OSCILLATION_UPPER ~ REDUCE_ZONE_UPPER  (建议卖出)
#   逃亡区: > REDUCE_ZONE_UPPER  (强制卖出)
class BIAS_THRESHOLDS:
    # 核心阈值 (优化后)
    DEEP_DIP = -6.0              # 原-10.0 → -6.0 (增加低吸机会)
    GOLD_ZONE_UPPER = -3.0       # 保持不变
    OSCILLATION_UPPER = 5.0      # 原8.0 → 5.0 (收窄震荡区)
    REDUCE_ZONE_UPPER = 12.0     # 原20.0 → 12.0 (更早开始减持)
    
    # 逃顶阈值 (优化后)
    ESCAPE_TOP_EXTREME = 25.0    # 原30.0 → 25.0 (极度疯狂，清仓60%)
    ESCAPE_TOP_HIGH = 15.0       # 原20.0 → 15.0 (疯狂，清仓40%)
    TREND_REVERSAL = 3.0         # 从上方跌破此值，切换回震荡吸筹逻辑

# 4. 仓位管理 (目标仓位百分比)
class TARGET_POSITION:
    DEEP_DIP = 0.95     # 深坑区: 95%仓位
    GOLD_ZONE = 0.75    # 黄金区: 75%仓位
    OSCILLATION = 0.55  # 震荡区: 55%仓位
    REDUCE_ZONE = 0.30  # 减持区: 30%仓位
    ESCAPE_ZONE = 0.0   # 逃亡区: 0%仓位 (触发即清仓)

# 5. 网格参数 (优化版 - 基于ETF实际波动特性)
# 网格间距 = ATR × 系数
# ETF日均波动约1-2%，ATR_14约为价格的1.5-3%
GRID_COEFFICIENT = {
    'DEEP_DIP': 0.8,     # 深坑区: 更小间距，激进抄底 (原1.2)
    'GOLD_ZONE': 1.0,    # 黄金区: 标准间距
    'OSCILLATION': 1.2,  # 震荡区: 稍大间距，避免过度交易 (原0.8)
    'REDUCE_ZONE': 1.5,  # 减持区: 较大间距，稳健卖出
}

# 动态间距参数 (基于ATR波动率)
# ETF波动率统计: 低波动<1.5%, 正常1.5-3%, 高波动>3%
class DYNAMIC_GRID:
    LOW_VOLATILITY_ATR = 0.015   # ATR < 1.5% 视为低波动 (原0.02)
    HIGH_VOLATILITY_ATR = 0.03   # ATR > 3% 视为高波动 (原0.05)
    LOW_VOL_MULTIPLIER = 0.8    # 低波动时间距缩小到80% (原0.7)
    HIGH_VOL_MULTIPLIER = 1.3   # 高波动时间距放大到130% (原1.5)

# 6. RSI 强弱指标配置 (新增)
class RSI_CONFIG:
    BUY_THRESHOLD = 30    # RSI < 30 超卖 (深坑区可适当放宽到 40)
    SELL_THRESHOLD = 75   # RSI > 75 超买 (禁止买入)

# 7. 动态止盈配置 (新增)
# 根据 ATR / Price 波动率动态调整止盈比例
class DYNAMIC_PROFIT_CONFIG:
    HIGH_VOLATILITY_PCT = 0.03   # 波动率 > 3%
    HIGH_PROFIT_TARGET = 0.020   # 高波动止盈 2.0%
    
    LOW_VOLATILITY_PCT = 0.015   # 波动率 < 1.5%
    LOW_PROFIT_TARGET = 0.010    # 低波动止盈 1.0%
    
    NORMAL_PROFIT_TARGET = 0.012 # 默认 1.2%

# 8. 趋势追踪参数 (新增)
class TREND_TRACKING:
    LOOKBACK_DAYS = 3            # 观察最近3天
    TREND_THRESHOLD = 2.0        # 每日变化 > 2% 视为趋势
    # 上涨趋势: 连续3天 BIAS 每日增长 > 2% → 暂停买入
    # 下跌趋势: 连续3天 BIAS 每日下降 > 2% → 暂停卖出

MIN_PROFIT_PCT = 0.012   # 最小利润保护: 1.2% (原0.8%，提高以覆盖滑点)
LOT_SIZE = 100           # 最小交易单位 (股)

# 7. 风控参数
MAX_DRAWDOWN_LIMIT = -0.20  # 单只ETF浮亏 > 20% 暂停买入

# ========================================
# 8. 实时监控配置
# ========================================

class MONITOR_CONFIG:
    # 监控刷新间隔 (秒)
    REFRESH_INTERVAL = 3          # 交易时段: 每3秒刷新一次（实时更新）
    REFRESH_INTERVAL_IDLE = 60   # 非交易时段: 每60秒刷新一次
    TRADING_START = "09:30"      # 交易开始时间
    TRADING_END = "15:00"        # 交易结束时间
    
    # 价格触发阈值
    PRICE_ALERT_PCT = 0.005     # 价格偏离网格价 0.5% 时提醒

# 9. 交易账户配置
class TRADE_CONFIG:
    ACCOUNT_ID = "40690541"     # QMT 账户ID
    AUTO_TRADE_ENABLED = True  # 自动下单开关 (默认关闭!)
    
    # 下单确认
    REQUIRE_CONFIRM = True      # 下单前需要确认
    MAX_ORDER_VALUE = 10000     # 单笔最大下单金额
    
    # 委托类型
    ORDER_PRICE_TYPE = "LIMIT"  # LIMIT-限价单, MARKET-市价单

# 10. 通知配置
class NOTIFY_CONFIG:
    # PushPlus 微信通知 (https://www.pushplus.plus/)
    PUSHPLUS_ENABLED = True
    PUSHPLUS_TOKEN = "995d6bf71f6f4e9b9da1b947af14ec3e"
    PUSHPLUS_TOPIC = ""         # 群组编码 (可选，留空发送给个人)
    
    # 控制台通知 (始终开启)
    CONSOLE_ENABLED = True
    
    # 通知级别
    NOTIFY_ON_SIGNAL = True     # 信号触发时通知
    NOTIFY_ON_TRADE = True      # 下单成功时通知
    NOTIFY_ON_ERROR = True      # 发生错误时通知