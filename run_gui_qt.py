# run_gui_qt.py - PyQt5 现代化 GUI
"""
BIAS-ATR 智能网格交易系统 - PyQt5 版本
深色主题 + 现代化布局
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QFrame, QSplitter, QListWidget,
    QListWidgetItem, QGroupBox, QGridLayout, QScrollArea, QMessageBox,
    QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon
import matplotlib
matplotlib.use('Qt5Agg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import threading

# 导入项目模块
import config
from data_manager import DataManager
from strategy import GridStrategy
from price_alert import alert_manager
from persistence import grid_state_manager
from logger import get_logger
from indicators import calculate_indicators


# 深色主题样式表
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0f0f0f;
    color: #e0e0e0;
    font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
}

QLabel {
    color: #e0e0e0;
}

QLabel#card-title {
    color: #888888;
    font-size: 12px;
}

QLabel#card-value {
    color: #ffffff;
    font-size: 24px;
    font-weight: bold;
}

QLabel#card-value-positive {
    color: #10b981;
    font-size: 24px;
    font-weight: bold;
}

QLabel#card-value-negative {
    color: #ef4444;
    font-size: 24px;
    font-weight: bold;
}

QFrame#card {
    background-color: #1a1a1a;
    border-radius: 12px;
    padding: 15px;
}

QFrame#panel {
    background-color: #1a1a1a;
    border-radius: 8px;
}

QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #3b82f6;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

QPushButton#btn-buy {
    background-color: #10b981;
}

QPushButton#btn-buy:hover {
    background-color: #059669;
}

QPushButton#btn-sell {
    background-color: #ef4444;
}

QPushButton#btn-sell:hover {
    background-color: #dc2626;
}

QTabWidget::pane {
    border: none;
    background-color: #1a1a1a;
}

QTabBar::tab {
    background-color: #1a1a1a;
    color: #888888;
    padding: 10px 25px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

QTabBar::tab:selected {
    background-color: #2563eb;
    color: white;
}

QTabBar::tab:hover:!selected {
    background-color: #333333;
}

QListWidget {
    background-color: #1a1a1a;
    border: none;
    border-radius: 8px;
}

QListWidget::item {
    padding: 10px;
    border-bottom: 1px solid #333333;
}

QListWidget::item:selected {
    background-color: #2563eb;
}

QListWidget::item:hover:!selected {
    background-color: #333333;
}

QScrollBar:vertical {
    background-color: #1a1a1a;
    width: 8px;
}

QScrollBar::handle:vertical {
    background-color: #444444;
    border-radius: 4px;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #333333;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #888888;
}

QProgressBar {
    background-color: #333333;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #10b981;
    border-radius: 4px;
}
"""


class ChartCanvas(FigureCanvas):
    """K线图表画布"""
    
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(8, 5), dpi=100, facecolor='#1a1a1a')
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)
        self.setup_style()
    
    def setup_style(self):
        """设置图表样式"""
        self.ax.set_facecolor('#1a1a1a')
        self.ax.tick_params(colors='#888888')
        self.ax.spines['bottom'].set_color('#333333')
        self.ax.spines['top'].set_color('#333333')
        self.ax.spines['left'].set_color('#333333')
        self.ax.spines['right'].set_color('#333333')
        self.ax.grid(True, color='#333333', linestyle='--', alpha=0.3)
    
    def plot_kline(self, df, orders=None, holdings=None):
        """绘制K线图"""
        self.ax.clear()
        self.setup_style()
        
        if df is None or df.empty:
            self.ax.text(0.5, 0.5, "暂无数据", transform=self.ax.transAxes,
                        color='#666666', ha='center', va='center', fontsize=14)
            self.draw()
            return
        
        # 取最近60条数据
        data = df.tail(60).copy()
        
        # 绘制K线
        width = 0.6
        width2 = 0.1
        
        up = data[data.close >= data.open]
        down = data[data.close < data.open]
        
        # 阳线(红)
        self.ax.bar(range(len(up)), up.close - up.open, width, 
                   bottom=up.open.values, color='#ef4444')
        self.ax.bar(range(len(up)), up.high - up.close, width2, 
                   bottom=up.close.values, color='#ef4444')
        self.ax.bar(range(len(up)), up.low - up.open, width2, 
                   bottom=up.open.values, color='#ef4444')
        
        # 阴线(绿)
        down_idx = [i for i, idx in enumerate(data.index) if idx in down.index]
        self.ax.bar(down_idx, (down.close - down.open).values, width, 
                   bottom=down.open.values, color='#10b981')
        
        # 绘制MA均线
        if 'ma_20' in data.columns:
            self.ax.plot(range(len(data)), data['ma_20'].values, 
                        color='#f59e0b', linewidth=1, alpha=0.7, label='MA20')
        
        # 绘制持仓成本线
        if holdings and holdings.get('avg_cost', 0) > 0 and holdings.get('volume', 0) > 0:
            cost = holdings['avg_cost']
            self.ax.axhline(y=cost, color='#a855f7', linestyle='-', linewidth=1.5, alpha=0.8)
            self.ax.text(len(data)-1, cost, f' 成本 {cost:.3f}', 
                        color='#a855f7', va='center', fontsize=8)
        
        # 绘制建议订单线
        if orders:
            for order in orders:
                price = order.price if hasattr(order, 'price') else order.get('price', 0)
                direction = order.direction if hasattr(order, 'direction') else order.get('direction', 'BUY')
                
                if direction == 'BUY':
                    color = '#10b981'
                    label = '买入'
                else:
                    color = '#ef4444'
                    label = '卖出'
                
                self.ax.axhline(y=price, color=color, linestyle='--', alpha=0.6)
                self.ax.text(len(data)-1, price, f' {label} {price:.3f}', 
                            color=color, va='center', fontsize=8)
        
        self.draw()


class SummaryCard(QFrame):
    """资产概览卡片"""
    
    def __init__(self, title, icon="💰", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(100)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题行
        title_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont('Segoe UI Emoji', 16))
        title_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setObjectName("card-title")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # 数值
        self.value_label = QLabel("--")
        self.value_label.setObjectName("card-value")
        layout.addWidget(self.value_label)
        
        # 副标题
        self.sub_label = QLabel("")
        self.sub_label.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(self.sub_label)
    
    def set_value(self, value, sub_text="", positive=None):
        """设置数值"""
        self.value_label.setText(value)
        self.sub_label.setText(sub_text)
        
        if positive is not None:
            if positive:
                self.value_label.setObjectName("card-value-positive")
            else:
                self.value_label.setObjectName("card-value-negative")
            self.value_label.setStyle(self.value_label.style())


class SignalItem(QWidget):
    """信号列表项"""
    
    def __init__(self, signal_data, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        # 方向标识
        direction = signal_data.get('direction', 'BUY')
        direction_label = QLabel("🟢" if direction == 'BUY' else "🔴")
        layout.addWidget(direction_label)
        
        # 主要信息
        info_layout = QVBoxLayout()
        
        name_label = QLabel(f"{signal_data.get('name', '')} {direction}")
        name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(name_label)
        
        price_text = f"¥{signal_data.get('target_price', 0):.3f} × {signal_data.get('amount', 0)}股"
        price_label = QLabel(price_text)
        price_label.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(price_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # 时间
        time_label = QLabel(signal_data.get('timestamp', '')[-8:])
        time_label.setStyleSheet("color: #666666; font-size: 10px;")
        layout.addWidget(time_label)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BIAS-ATR 智能网格交易系统")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 800)
        
        # 初始化数据
        self.data_manager = DataManager()
        self.strategy = GridStrategy()
        self.logger = get_logger()
        self.etf_data = {}
        self.current_etf = config.ETF_LIST[0] if config.ETF_LIST else None
        
        # 设置UI
        self.setup_ui()
        
        # 启动数据刷新
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(3000)  # 3秒刷新
        
        # 首次加载
        self.refresh_data()
    
    def setup_ui(self):
        """设置UI"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # 1. 顶部卡片
        self.setup_summary_cards(main_layout)
        
        # 2. 主内容区
        self.setup_main_content(main_layout)
        
        # 3. 底部ETF切换
        self.setup_etf_tabs(main_layout)
    
    def setup_summary_cards(self, layout):
        """顶部资产卡片"""
        cards_layout = QHBoxLayout()
        
        self.card_asset = SummaryCard("总资产", "💼")
        self.card_profit = SummaryCard("总盈亏", "📈")
        self.card_day = SummaryCard("今日收益", "🌟")
        self.card_signals = SummaryCard("交易信号", "🔔")
        
        cards_layout.addWidget(self.card_asset)
        cards_layout.addWidget(self.card_profit)
        cards_layout.addWidget(self.card_day)
        cards_layout.addWidget(self.card_signals)
        
        layout.addLayout(cards_layout)
    
    def setup_main_content(self, layout):
        """主内容区"""
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：图表
        chart_frame = QFrame()
        chart_frame.setObjectName("panel")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(10, 10, 10, 10)
        
        self.chart = ChartCanvas()
        chart_layout.addWidget(self.chart)
        
        splitter.addWidget(chart_frame)
        
        # 右侧：信号+交易
        right_frame = QFrame()
        right_frame.setObjectName("panel")
        right_frame.setMaximumWidth(350)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # 信号列表
        signals_group = QGroupBox("📋 交易信号")
        signals_layout = QVBoxLayout(signals_group)
        
        self.signals_list = QListWidget()
        self.signals_list.setMinimumHeight(200)
        signals_layout.addWidget(self.signals_list)
        
        right_layout.addWidget(signals_group)
        
        # 快速交易
        trade_group = QGroupBox("⚡ 快速交易")
        trade_layout = QVBoxLayout(trade_group)
        
        self.etf_label = QLabel("未选择 ETF")
        self.etf_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        trade_layout.addWidget(self.etf_label)
        
        btn_layout = QHBoxLayout()
        
        btn_buy = QPushButton("买入")
        btn_buy.setObjectName("btn-buy")
        btn_buy.clicked.connect(lambda: self.quick_trade('BUY'))
        btn_layout.addWidget(btn_buy)
        
        btn_sell = QPushButton("卖出")
        btn_sell.setObjectName("btn-sell")
        btn_sell.clicked.connect(lambda: self.quick_trade('SELL'))
        btn_layout.addWidget(btn_sell)
        
        trade_layout.addLayout(btn_layout)
        right_layout.addWidget(trade_group)
        
        # 详情按钮
        btn_detail = QPushButton("📊 查看详情")
        btn_detail.clicked.connect(self.show_detail)
        right_layout.addWidget(btn_detail)
        
        right_layout.addStretch()
        
        splitter.addWidget(right_frame)
        splitter.setSizes([900, 350])
        
        layout.addWidget(splitter)
    
    def setup_etf_tabs(self, layout):
        """底部ETF切换标签"""
        self.etf_tabs = QTabWidget()
        self.etf_tabs.setMaximumHeight(50)
        
        for code in config.ETF_LIST:
            name = config.ETF_NAMES.get(code, code)
            self.etf_tabs.addTab(QWidget(), name)
        
        self.etf_tabs.currentChanged.connect(self.on_etf_changed)
        layout.addWidget(self.etf_tabs)
    
    def on_etf_changed(self, index):
        """ETF切换"""
        if 0 <= index < len(config.ETF_LIST):
            self.current_etf = config.ETF_LIST[index]
            name = config.ETF_NAMES.get(self.current_etf, self.current_etf)
            self.etf_label.setText(f"{name} ({self.current_etf})")
            self.update_chart()
    
    def refresh_data(self):
        """刷新数据"""
        try:
            for code in config.ETF_LIST:
                df = self.data_manager.get_history(code, count=100, use_cache=True)
                if df.empty:
                    continue
                
                df = calculate_indicators(df)
                holdings = config.REAL_HOLDINGS.get(code, {'volume': 0, 'avg_cost': 0, 'available': 0})
                plan = self.strategy.analyze(code, df, holdings)
                
                # 检查价格提醒
                name = config.ETF_NAMES.get(code, code)
                alert_manager.check_price_alerts(
                    code, name, plan.current_price,
                    [{'direction': o.direction, 'price': o.price, 'amount': o.amount, 'desc': o.desc}
                     for o in plan.suggested_orders]
                )
                
                self.etf_data[code] = {
                    'name': name,
                    'price': plan.current_price,
                    'bias': plan.current_bias,
                    'status': plan.market_status,
                    'holdings': holdings,
                    'orders': plan.suggested_orders,
                    'df': df,
                    'plan': plan
                }
            
            self.update_ui()
            
        except Exception as e:
            print(f"数据刷新错误: {e}")
    
    def update_ui(self):
        """更新UI"""
        # 计算汇总
        total_value = 0
        total_floating = 0
        
        for code, data in self.etf_data.items():
            holdings = data['holdings']
            vol = holdings.get('volume', 0)
            price = data['price']
            cost = holdings.get('avg_cost', 0)
            
            total_value += price * vol
            if cost > 0 and vol > 0:
                total_floating += (price - cost) * vol
        
        # 获取已实现盈亏
        all_realized = grid_state_manager.get_realized_pnl()
        today_realized = grid_state_manager.get_realized_pnl(
            start_date=datetime.now().strftime('%Y-%m-%d')
        )
        
        total_profit = total_floating + all_realized
        total_asset = config.TOTAL_CAPITAL + total_profit
        
        # 更新卡片
        self.card_asset.set_value(f"¥{total_asset:,.0f}", f"持仓: ¥{total_value:,.0f}")
        self.card_profit.set_value(
            f"{'+' if total_profit >= 0 else ''}¥{total_profit:,.0f}",
            f"浮盈: ¥{total_floating:,.0f}",
            positive=total_profit >= 0
        )
        self.card_day.set_value(
            f"{'+' if today_realized >= 0 else ''}¥{today_realized:,.0f}",
            "今日已实现",
            positive=today_realized >= 0
        )
        
        # 信号统计
        alerts = alert_manager.get_recent_alerts(24)
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_count = len([a for a in alerts if a.timestamp.strftime('%Y-%m-%d') == today_str])
        self.card_signals.set_value(str(len(alerts)), f"今日新增: {today_count}")
        
        # 更新信号列表
        self.update_signals(alerts[:10])
        
        # 更新图表
        self.update_chart()
    
    def update_signals(self, alerts):
        """更新信号列表"""
        self.signals_list.clear()
        
        for alert in alerts:
            signal_data = {
                'name': getattr(alert, 'name', ''),
                'direction': getattr(alert, 'direction', 'BUY'),
                'target_price': getattr(alert, 'target_price', 0) or 0,
                'amount': getattr(alert, 'amount', 0) or 0,
                'timestamp': alert.timestamp.strftime('%H:%M:%S') if hasattr(alert, 'timestamp') else ''
            }
            
            item = QListWidgetItem()
            widget = SignalItem(signal_data)
            item.setSizeHint(widget.sizeHint())
            self.signals_list.addItem(item)
            self.signals_list.setItemWidget(item, widget)
    
    def update_chart(self):
        """更新图表"""
        if self.current_etf and self.current_etf in self.etf_data:
            data = self.etf_data[self.current_etf]
            self.chart.plot_kline(
                data.get('df'),
                data.get('orders'),
                data.get('holdings')
            )
    
    def quick_trade(self, direction):
        """快速交易"""
        if not self.current_etf:
            QMessageBox.warning(self, "提示", "请先选择ETF")
            return
        
        name = config.ETF_NAMES.get(self.current_etf, self.current_etf)
        action = "买入" if direction == 'BUY' else "卖出"
        
        reply = QMessageBox.question(
            self, "确认交易",
            f"确定要【{action}】 {name} ({self.current_etf}) 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "提示", f"交易功能开发中...\n\n{action} {name}")
    
    def show_detail(self):
        """显示详情"""
        if not self.current_etf or self.current_etf not in self.etf_data:
            return
        
        data = self.etf_data[self.current_etf]
        holdings = data['holdings']
        
        # 计算浮盈
        floating_pnl = 0
        if holdings.get('volume', 0) > 0 and holdings.get('avg_cost', 0) > 0:
            floating_pnl = (data['price'] - holdings['avg_cost']) * holdings['volume']
        
        detail = f"""
═══════════════════════════════
     {data['name']} ({self.current_etf})
═══════════════════════════════

【基本信息】
  当前价格: ¥{data['price']:.3f}
  BIAS指标: {data['bias']:.2f}%
  市场状态: {data['status']}

【持仓信息】
  持仓数量: {holdings.get('volume', 0):,}股
  平均成本: ¥{holdings.get('avg_cost', 0):.3f}
  浮动盈亏: {'+' if floating_pnl >= 0 else ''}¥{floating_pnl:,.2f}

【建议订单】
"""
        for order in data.get('orders', []):
            price = order.price if hasattr(order, 'price') else order.get('price', 0)
            amount = order.amount if hasattr(order, 'amount') else order.get('amount', 0)
            direction = order.direction if hasattr(order, 'direction') else order.get('direction', '')
            icon = "🟢" if direction == 'BUY' else "🔴"
            detail += f"  {icon} ¥{price:.3f} × {amount}股\n"
        
        QMessageBox.information(self, f"ETF详情 - {data['name']}", detail)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    
    # 设置高DPI支持
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    print("=" * 50)
    print("BIAS-ATR 智能网格交易系统 (PyQt5)")
    print("=" * 50)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
