# 真实数据配置指南

本指南将帮助您配置真实的ETF数据和交易接口，让系统从演示模式升级到生产环境。

## 📋 前置要求

### 环境准备
- Python 3.8+
- 稳定的网络连接
- 证券账户（用于交易功能）

### 安装依赖
```bash
pip install pandas numpy matplotlib akshare tushare
```

## 🔗 数据源配置

### 方案一：使用 akshare（推荐，免费）

#### 1. 安装 akshare
```bash
pip install akshare
```

#### 2. 配置数据源
编辑 `config.py` 文件，设置数据源类型：

```python
# 数据源配置
DATA_SOURCE = 'akshare'  # 设置为 'akshare'
```

#### 3. 测试数据获取
```python
import akshare as ak
# 测试获取ETF数据
df = ak.fund_etf_hist_sina(symbol="510300")
print(df.head())
```

### 方案二：使用 tushare（需要token）

#### 1. 注册 tushare
访问 https://tushare.pro/register 注册账户

#### 2. 获取token
- 登录后在个人中心获取API token
- 免费账户有调用次数限制

#### 3. 配置tushare
```python
import tushare as ts

# 设置token
ts.set_token('your_token_here')
pro = ts.pro_api()

# 测试接口
df = pro.daily(ts_code='510300.SZ')
print(df.head())
```

#### 4. 修改配置文件
编辑 `config.py`：

```python
# 数据源配置
DATA_SOURCE = 'tushare'
TUSHARE_TOKEN = 'your_token_here'
```

## 💼 交易接口配置

### 方案一：使用 QMT/XtTrader

#### 1. 安装 QMT 客户端
- 下载并安装迅投QMT交易客户端
- 确保能够正常登录和交易

#### 2. 安装 XtTrader
```bash
# 如果有交易需求，需要安装交易接口包
# 这通常需要特定的券商支持
```

#### 3. 配置交易参数
编辑 `config.py`：

```python
# 交易配置
TRADE_CONFIG = {
    'ENABLED': True,  # 启用交易功能
    'ACCOUNT_ID': 'your_account_id',  # 交易账户
    'AUTO_TRADE': False,  # 是否启用自动交易
    'MAX_SINGLE_AMOUNT': 10000,  # 单次最大交易金额
    'MAX_DAILY_TRADES': 10,  # 单日最大交易次数
}
```

### 方案二：仅监控模式（推荐新手）

```python
# 交易配置
TRADE_CONFIG = {
    'ENABLED': False,  # 禁用交易功能
    'AUTO_TRADE': False,
}
```

## 📊 ETF配置

### 1. 配置监控ETF列表
编辑 `config.py`：

```python
# ETF监控列表
ETF_LIST = [
    '510300',  # 沪深300ETF
    '159919',  # 沪深300ETF
    '510500',  # 中证500ETF
    '159915',  # 创业板ETF
    '512100',  # 中证1000ETF
    # 可以添加更多ETF
]

# ETF名称映射
ETF_NAMES = {
    '510300': '沪深300ETF',
    '159919': '沪深300ETF',
    '510500': '中证500ETF',
    '159915': '创业板ETF',
    '512100': '中证1000ETF',
}
```

### 2. 配置资金参数
```python
# 资金配置
TOTAL_CAPITAL = 200000  # 总资金（20万）
CAPITAL_PER_ETF = 40000  # 每只ETF分配资金（4万）

# 手续费配置
COMMISSION_RATE = 0.0003  # 手续费率（万三）
MIN_COMMISSION = 5  # 最低手续费（5元）
```

## 🎯 策略参数配置

### 1. BIAS阈值设置
```python
# BIAS阈值配置
BIAS_THRESHOLDS = {
    'DEEP_DIP': -8,        # 深坑区上限
    'GOLD_ZONE_UPPER': -3, # 黄金区上限
    'OSCILLATION_UPPER': 2, # 震荡区上限
    'REDUCE_ZONE_UPPER': 5, # 减持区上限
    'TREND_REVERSAL': 3    # 趋势反转点
}
```

### 2. 目标仓位设置
```python
# 目标仓位配置
TARGET_POSITION = {
    'DEEP_DIP': 0.8,      # 深坑区目标仓位 80%
    'GOLD_ZONE': 0.6,     # 黄金区目标仓位 60%
    'OSCILLATION': 0.5,   # 震荡区目标仓位 50%
    'REDUCE_ZONE': 0.3,   # 减持区目标仓位 30%
    'ESCAPE_ZONE': 0.1    # 逃亡区目标仓位 10%
}
```

## 🔧 启动真实数据版本

### 1. Web监控面板
```bash
python web_server.py
```
然后访问 http://localhost:5000

### 2. 桌面GUI应用
```bash
python gui_main.py
```

### 3. 检查配置
启动后检查控制台输出，确认：
- 数据源连接正常
- ETF数据获取成功
- 策略计算正确
- 价格提醒功能正常

## 📝 配置文件示例

### 完整的 config.py 示例
```python
# config.py - 完整配置示例

# 数据源配置
DATA_SOURCE = 'akshare'  # 'akshare' 或 'tushare'
TUSHARE_TOKEN = 'your_tushare_token_here'  # 仅tushare需要

# ETF监控列表
ETF_LIST = [
    '510300',  # 沪深300ETF
    '159919',  # 沪深300ETF
    '510500',  # 中证500ETF
    '159915',  # 创业板ETF
]

# ETF名称映射
ETF_NAMES = {
    '510300': '沪深300ETF',
    '159919': '沪深300ETF',
    '510500': '中证500ETF',
    '159915': '创业板ETF',
}

# 资金配置
TOTAL_CAPITAL = 200000
CAPITAL_PER_ETF = 40000

# 交易配置
TRADE_CONFIG = {
    'ENABLED': False,  # 建议先设为False，熟悉系统后再开启
    'ACCOUNT_ID': '',
    'AUTO_TRADE': False,
    'MAX_SINGLE_AMOUNT': 10000,
    'MAX_DAILY_TRADES': 10,
}

# BIAS阈值
BIAS_THRESHOLDS = {
    'DEEP_DIP': -8,
    'GOLD_ZONE_UPPER': -3,
    'OSCILLATION_UPPER': 2,
    'REDUCE_ZONE_UPPER': 5,
    'TREND_REVERSAL': 3,
}

# 目标仓位
TARGET_POSITION = {
    'DEEP_DIP': 0.8,
    'GOLD_ZONE': 0.6,
    'OSCILLATION': 0.5,
    'REDUCE_ZONE': 0.3,
    'ESCAPE_ZONE': 0.1,
}

# 手续费配置
COMMISSION_RATE = 0.0003
MIN_COMMISSION = 5

# 监控配置
MONITOR_CONFIG = {
    'REFRESH_INTERVAL': 10,  # 数据刷新间隔（秒）
    'ALERT_ENABLED': True,    # 启用价格提醒
}

# 持仓数据（可以手动设置或从文件加载）
REAL_HOLDINGS = {
    '510300': {
        'volume': 1000,
        'available': 1000,
        'avg_cost': 3.500
    },
    '159919': {
        'volume': 0,
        'available': 0,
        'avg_cost': 0
    },
}
```

## 🚨 风险提示

### 1. 数据延迟
- 免费数据源可能有15-20分钟延迟
- 建议使用付费数据源获取实时数据

### 2. 交易风险
- 自动交易功能请谨慎启用
- 建议先在模拟环境测试
- 设置合理的交易限额

### 3. 系统稳定性
- 定期备份配置文件
- 监控系统运行状态
- 设置异常提醒

## 🔍 故障排除

### 1. 数据获取失败
```bash
# 检查网络连接
ping www.baidu.com

# 测试akshare
python -c "import akshare as ak; print(ak.tool_trade_date_hist_sina())"

# 测试tushare
python -c "import tushare as ts; print(ts.get_k_data('510300'))"
```

### 2. 策略计算错误
```bash
# 检查指标计算
python -c "from indicators import calculate_indicators; import pandas as pd; print('指标计算正常')"
```

### 3. Web服务无法启动
```bash
# 检查端口占用
netstat -ano | findstr :5000

# 更换端口
python web_server.py --port 8080
```

## 📞 技术支持

如果配置过程中遇到问题：

1. 查看控制台错误信息
2. 检查网络连接状态
3. 确认配置文件格式正确
4. 参考官方文档和社区资源

---

**⚠️ 重要提醒**：
- 请在充分测试后启用交易功能
- 建议从小资金开始
- 时刻监控系统运行状态
- 及时备份重要数据