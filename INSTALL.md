# 安装与使用指南

## 环境要求

- Python 3.7 或更高版本
- Windows、macOS 或 Linux 操作系统

## 安装步骤

### 1. 克隆或下载项目

如果您使用 Git:
```bash
git clone <项目地址>
```

或者直接下载项目压缩包并解压。

### 2. 安装依赖

进入项目目录并安装所需依赖:

```bash
cd BIAS-ATR-Grid-Trader
pip install -r requirements.txt
```

### 3. 安装 akshare (可选但推荐)

为了获取真实的A股ETF数据，建议安装 akshare:

```bash
pip install akshare
```

注意: akshare 依赖较多，安装可能需要一些时间。

## 运行项目

### 基本运行

```bash
python main.py
```

程序将自动获取ETF数据并生成交易计划。

### 查看结果

运行后，程序会在控制台输出详细的交易计划，包括:
- 每只ETF的当前状态和建议操作
- 买入和卖出价位
- 风险提示信息

## 配置说明

### 修改ETF列表

在 `config.py` 文件中修改 `ETF_LIST` 变量:

```python
ETF_LIST = [
    '510300.SH',  # 沪深300ETF
    '510500.SH',  # 中证500ETF
    # 添加或删除ETF代码
]
```

### 调整资金参数

在 `config.py` 中修改资金相关参数:

```python
TOTAL_CAPITAL = 200000  # 总资金
```

### 调整策略参数

可以根据需要调整BIAS阈值、仓位目标等参数。

## 故障排除

### 1. 无法获取真实数据

如果看到类似以下信息:
```
Using Mock Data...
```

这表示程序无法从网络获取真实数据，而是使用模拟数据进行演示。这可能是由于:

- 网络连接问题
- akshare未正确安装
- 数据源服务器暂时不可用

解决方法:
1. 检查网络连接
2. 重新安装akshare: `pip install akshare --upgrade`
3. 稍后再试

### 2. 缺少依赖包

如果运行时出现导入错误，尝试重新安装依赖:

```bash
pip install -r requirements.txt --upgrade
```

### 3. 编码问题

如果在Windows上出现中文编码问题，可以在运行前设置环境变量:

```bash
set PYTHONIOENCODING=utf-8
python main.py
```

## 使用建议

1. **初始使用**: 建议首次运行时使用模拟数据熟悉策略逻辑
2. **参数调优**: 根据实际市场情况和个人风险偏好调整参数
3. **风险管理**: 严格按照策略执行，注意风险控制规则
4. **定期更新**: 定期更新akshare以获取最新数据接口

## 免责声明

本项目仅供学习研究使用，不构成投资建议。使用者应自行承担投资风险。