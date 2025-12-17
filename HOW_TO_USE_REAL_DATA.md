# 如何使用真实数据 - 快速指南

## 🚀 快速开始

### 1. 运行配置脚本
```bash
python setup_real_data_simple.py
```
选择数据源（推荐选择 `1` - akshare）

### 2. 验证配置
```bash
# 测试数据获取
python -c "import akshare as ak; print('数据源配置成功')"
```

### 3. 启动系统

#### Web监控面板（推荐）
```bash
python web_server.py
```
然后访问：http://localhost:5000

#### 桌面GUI应用
```bash
python gui_main.py
```

## 📊 数据源选择

### Akshare（推荐新手）
✅ **优点**：
- 完全免费
- 无需注册
- 数据覆盖面广
- 更新及时

❌ **缺点**：
- 可能有延迟（15-20分钟）
- 免费版本有限制

### Tushare（专业用户）
✅ **优点**：
- 数据质量高
- 实时性较好
- 专业金融数据

❌ **缺点**：
- 需要注册
- 免费额度有限
- 付费接口

## 🔧 配置示例

### 基础配置（config.py）
```python
# 数据源选择
DATA_SOURCE = 'akshare'  # 或 'tushare'

# Tushare配置（如果使用）
TUSHARE_TOKEN = 'your_token_here'

# ETF监控列表
ETF_LIST = [
    '510300',  # 沪深300ETF
    '159919',  # 沪深300ETF
    '510500',  # 中证500ETF
]

# 资金配置
TOTAL_CAPITAL = 200000  # 总资金20万
CAPITAL_PER_ETF = 40000  # 每只ETF 4万
```

## 🎯 使用场景

### 场景1：首次使用（新手）
```bash
# 1. 配置数据源
python setup_real_data_simple.py

# 2. 运行演示版熟悉界面
python run_gui.py

# 3. 切换到真实数据
python web_server.py
```

### 场景2：日常监控
```bash
# 启动Web监控
python web_server.py

# 访问 http://localhost:5000
# 查看实时价格和网格建议
# 接收价格提醒通知
```

### 场景3：专业分析
```bash
# 配置tushare专业数据源
# 启动完整版GUI
python gui_main.py

# 使用数据分析功能
# 查看详细图表
# 导出分析报告
```

## 📱 界面使用

### Web监控面板
1. **主页面**：http://localhost:5000
2. **实时数据**：自动刷新ETF价格
3. **网格建议**：显示买1、买2、卖1、卖2建议
4. **价格提醒**：当价格触及网格点时通知
5. **手动交易**：支持Web端下单操作

### 桌面GUI应用
1. **启动**：`python gui_main.py`
2. **监控面板**：左侧ETF数据表格
3. **提醒窗口**：右侧价格提醒
4. **快捷操作**：一键刷新、交易等
5. **设置菜单**：配置参数和偏好

## ⚠️ 重要提醒

### 数据延迟
- akshare数据通常有15-20分钟延迟
- 非实时数据，不适合日内高频交易
- 适合中长期网格策略

### 交易风险
- 建议先在模拟环境测试
- 使用小额资金开始
- 不要启用自动交易（除非充分测试）

### 系统稳定
- 定期检查网络连接
- 监控系统运行状态
- 及时更新配置参数

## 🔍 故障排除

### 1. 数据获取失败
```bash
# 检查网络连接
ping www.baidu.com

# 测试akshare
python -c "import akshare as ak; print(ak.__version__)"

# 重新安装
pip install --upgrade akshare
```

### 2. Web服务无法启动
```bash
# 检查端口占用
netstat -ano | findstr :5000

# 更换端口
python web_server.py --port 8080
```

### 3. GUI界面异常
```bash
# 检查tkinter
python -c "import tkinter; print('tkinter正常')"

# 更新相关包
pip install --upgrade matplotlib pillow
```

## 📚 进阶功能

### 1. 自定义ETF列表
编辑 `config.py`：
```python
ETF_LIST = [
    '510300',  # 沪深300ETF
    '510500',  # 中证500ETF
    '159915',  # 创业板ETF
    '512100',  # 中证1000ETF
    # 添加你关注的ETF
]
```

### 2. 调整策略参数
```python
# BIAS阈值
BIAS_THRESHOLDS = {
    'DEEP_DIP': -8,        # 深坑区
    'GOLD_ZONE_UPPER': -3, # 黄金区
    'OSCILLATION_UPPER': 2, # 震荡区
    'REDUCE_ZONE_UPPER': 5, # 减持区
}

# 目标仓位
TARGET_POSITION = {
    'DEEP_DIP': 0.8,     # 深坑区80%仓位
    'GOLD_ZONE': 0.6,    # 黄金区60%仓位
    'OSCILLATION': 0.5,  # 震荡区50%仓位
    'REDUCE_ZONE': 0.3,  # 减持区30%仓位
}
```

### 3. 设置价格提醒
```python
# 在config.py中添加
NOTIFY_CONFIG = {
    'price_alert_enabled': True,
    'alert_interval': 60,  # 同价位提醒间隔（分钟）
    'sound_enabled': True,
}
```

## 🎯 最佳实践

### 1. 资金管理
- 单只ETF不超过总资金的20%
- 保留充足的备用金
- 分散投资降低风险

### 2. 策略执行
- 严格按照网格建议操作
- 不要追涨杀跌
- 保持纪律性

### 3. 监控调整
- 定期检查策略表现
- 根据市场情况调整参数
- 及时止盈止损

---

**开始使用**：
1. 运行 `python setup_real_data_simple.py` 配置数据源
2. 执行 `python web_server.py` 启动Web监控
3. 访问 http://localhost:5000 开始使用

**获得帮助**：
- 查看 `README_GUI.md` 了解详细功能
- 查看 `SETUP_REAL_DATA.md` 了解配置选项
- 检查控制台输出了解运行状态