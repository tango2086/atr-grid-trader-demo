# gui_dialogs.py - GUI对话框和子窗口
"""
包含各种对话框和子窗口的详细实现：
- 交易对话框
- 设置界面
- 数据分析窗口
- 提醒历史窗口
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime, timedelta
import json

from price_alert import alert_manager
from trader import get_trader, HAS_TRADER
import config

class TradeDialog:
    """交易对话框"""

    def __init__(self, parent, etf_data=None):
        self.parent = parent
        self.etf_data = etf_data or {}
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("手动下单")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.create_widgets()

    def create_widgets(self):
        """创建组件"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ETF选择
        ttk.Label(main_frame, text="ETF代码:", font=('Microsoft YaHei', 10)).grid(row=0, column=0, sticky=tk.W, pady=5)

        self.code_var = tk.StringVar()
        self.code_combo = ttk.Combobox(main_frame, textvariable=self.code_var, width=20)
        self.code_combo['values'] = list(config.ETF_LIST) + list(config.ETF_NAMES.keys())
        self.code_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        self.code_combo.bind('<<ComboboxSelected>>', self.on_etf_selected)

        # 名称显示
        ttk.Label(main_frame, text="ETF名称:", font=('Microsoft YaHei', 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar(value="--")
        ttk.Label(main_frame, textvariable=self.name_var).grid(row=1, column=1, sticky=tk.W, pady=5)

        # 当前价格
        ttk.Label(main_frame, text="当前价格:", font=('Microsoft YaHei', 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.price_var = tk.StringVar(value="--")
        ttk.Label(main_frame, textvariable=self.price_var).grid(row=2, column=1, sticky=tk.W, pady=5)

        # 交易方向
        ttk.Label(main_frame, text="交易方向:", font=('Microsoft YaHei', 10)).grid(row=3, column=0, sticky=tk.W, pady=5)

        direction_frame = ttk.Frame(main_frame)
        direction_frame.grid(row=3, column=1, sticky=tk.W, pady=5)

        self.direction_var = tk.StringVar(value="BUY")
        ttk.Radiobutton(direction_frame, text="买入", variable=self.direction_var, value="BUY").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(direction_frame, text="卖出", variable=self.direction_var, value="SELL").pack(side=tk.LEFT)

        # 交易价格
        ttk.Label(main_frame, text="交易价格:", font=('Microsoft YaHei', 10)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.trade_price_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.trade_price_var, width=20).grid(row=4, column=1, sticky=tk.W, pady=5)

        # 交易数量
        ttk.Label(main_frame, text="交易数量:", font=('Microsoft YaHei', 10)).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.volume_var = tk.StringVar()
        volume_frame = ttk.Frame(main_frame)
        volume_frame.grid(row=5, column=1, sticky=tk.W, pady=5)

        ttk.Entry(volume_frame, textvariable=self.volume_var, width=15).pack(side=tk.LEFT)
        ttk.Label(volume_frame, text="股").pack(side=tk.LEFT, padx=(5, 0))

        # 快速数量按钮
        quick_volume_frame = ttk.Frame(main_frame)
        quick_volume_frame.grid(row=6, column=1, sticky=tk.W, pady=5)

        ttk.Label(quick_volume_frame, text="快速:", font=('Microsoft YaHei', 9)).pack(side=tk.LEFT, padx=(0, 5))
        for volume in [100, 500, 1000, 2000]:
            ttk.Button(quick_volume_frame, text=f"{volume}", width=8,
                      command=lambda v=volume: self.volume_var.set(str(v))).pack(side=tk.LEFT, padx=2)

        # 交易金额
        ttk.Label(main_frame, text="交易金额:", font=('Microsoft YaHei', 10)).grid(row=7, column=0, sticky=tk.W, pady=5)
        self.amount_var = tk.StringVar(value="¥0")
        ttk.Label(main_frame, textvariable=self.amount_var).grid(row=7, column=1, sticky=tk.W, pady=5)

        # 绑定价格和数量变化事件
        self.trade_price_var.trace('w', self.calculate_amount)
        self.volume_var.trace('w', self.calculate_amount)

        # 网格建议
        grid_frame = ttk.LabelFrame(main_frame, text="网格建议", padding="10")
        grid_frame.grid(row=8, column=0, columnspan=2, sticky=tk.W+tk.E, pady=10)

        self.grid_text = tk.Text(grid_frame, height=6, width=50)
        self.grid_text.pack(fill=tk.BOTH, expand=True)

        # 按钮栏
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=9, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="使用网格建议", command=self.use_grid_suggestion).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="确认下单", command=self.confirm_trade).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)

    def on_etf_selected(self, event=None):
        """ETF选择事件"""
        code = self.code_var.get()
        name = config.ETF_NAMES.get(code, code)
        self.name_var.set(name)

        # 更新当前价格
        if code in self.etf_data:
            current_price = self.etf_data[code]['price']
            self.price_var.set(f"{current_price:.3f}")
            self.trade_price_var.set(f"{current_price:.3f}")

            # 显示网格建议
            self.show_grid_suggestion(code)

    def show_grid_suggestion(self, code):
        """显示网格建议"""
        if code not in self.etf_data:
            return

        self.grid_text.delete(1.0, tk.END)

        etf_info = self.etf_data[code]
        orders = etf_info.get('orders', [])

        suggestion_text = f"ETF: {etf_info['name']} ({code})\n"
        suggestion_text += f"当前价格: ¥{etf_info['price']:.3f}\n"
        suggestion_text += f"市场状态: {etf_info['status']}\n\n"

        if orders:
            suggestion_text += "网格建议:\n"
            for i, order in enumerate(orders, 1):
                icon = "🔵" if order.direction == 'BUY' else "🔴"
                suggestion_text += f"{icon} {order.direction} {order.price:.3f} × {order.amount}股 ({order.desc})\n"
        else:
            suggestion_text += "暂无网格建议\n"

        # 添加警告信息
        warnings = etf_info.get('warnings', [])
        if warnings:
            suggestion_text += "\n⚠️ 风险提示:\n"
            for warning in warnings:
                suggestion_text += f"• {warning}\n"

        self.grid_text.insert(1.0, suggestion_text)

    def use_grid_suggestion(self):
        """使用网格建议"""
        code = self.code_var.get()
        if code not in self.etf_data:
            messagebox.showwarning("提示", "请先选择ETF")
            return

        orders = self.etf_data[code].get('orders', [])
        if not orders:
            messagebox.showinfo("提示", "暂无网格建议")
            return

        direction = self.direction_var.get()
        matching_orders = [o for o in orders if o.direction == direction]

        if matching_orders:
            # 使用第一个匹配的订单
            order = matching_orders[0]
            self.trade_price_var.set(f"{order.price:.3f}")
            self.volume_var.set(str(order.amount))
        else:
            messagebox.showinfo("提示", f"没有找到{direction}方向的网格建议")

    def calculate_amount(self, *args):
        """计算交易金额"""
        try:
            price = float(self.trade_price_var.get() or 0)
            volume = int(self.volume_var.get() or 0)
            amount = price * volume
            self.amount_var.set(f"¥{amount:,.0f}")
        except ValueError:
            self.amount_var.set("¥0")

    def confirm_trade(self):
        """确认交易"""
        try:
            code = self.code_var.get()
            direction = self.direction_var.get()
            price = float(self.trade_price_var.get())
            volume = int(self.volume_var.get())

            if not code:
                messagebox.showwarning("错误", "请选择ETF")
                return

            if price <= 0:
                messagebox.showwarning("错误", "请输入有效的交易价格")
                return

            if volume <= 0:
                messagebox.showwarning("错误", "请输入有效的交易数量")
                return

            # 确认对话框
            confirm_msg = f"""
确认交易信息：

ETF: {config.ETF_NAMES.get(code, code)} ({code})
方向: {'买入' if direction == 'BUY' else '卖出'}
价格: ¥{price:.3f}
数量: {volume}股
金额: ¥{price*volume:,.0f}

是否确认下单？
            """

            if messagebox.askyesno("确认交易", confirm_msg):
                # 执行交易
                self.execute_trade(code, direction, price, volume)

        except ValueError as e:
            messagebox.showerror("错误", f"输入数据无效: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"交易失败: {e}")

    def execute_trade(self, code, direction, price, volume):
        """执行交易"""
        try:
            if not HAS_TRADER:
                messagebox.showerror("错误", "交易模块未启用，无法下单")
                return

            trader = get_trader()
            if not trader.is_connected():
                if not trader.connect():
                    messagebox.showerror("错误", "交易服务连接失败")
                    return

            result = trader.place_order(code, direction, price, volume, confirm=False)

            if result.success:
                messagebox.showinfo("成功", f"下单成功！\n订单号: {result.order_id}")
                self.result = result
                self.dialog.destroy()
            else:
                messagebox.showerror("失败", f"下单失败: {result.message}")

        except Exception as e:
            messagebox.showerror("错误", f"执行交易失败: {e}")

class SettingsDialog:
    """设置对话框"""

    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("系统设置")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 创建笔记本组件（标签页）
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.create_tabs()

        # 底部按钮
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="保存设置", command=self.save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="重置默认", command=self.reset_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def create_tabs(self):
        """创建设置标签页"""
        # 基础设置
        self.create_basic_settings()

        # 策略设置
        self.create_strategy_settings()

        # 提醒设置
        self.create_alert_settings()

        # 交易设置
        self.create_trade_settings()

    def create_basic_settings(self):
        """创建基础设置页"""
        basic_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(basic_frame, text="基础设置")

        # 数据源设置
        ttk.Label(basic_frame, text="数据源设置", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(basic_frame, text="数据源类型:").pack(anchor=tk.W)
        self.data_source_var = tk.StringVar(value="akshare")
        data_source_frame = ttk.Frame(basic_frame)
        data_source_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Radiobutton(data_source_frame, text="akshare (推荐)", variable=self.data_source_var, value="akshare").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(data_source_frame, text="tushare", variable=self.data_source_var, value="tushare").pack(side=tk.LEFT)

        # 刷新间隔
        ttk.Label(basic_frame, text="数据刷新间隔 (秒):").pack(anchor=tk.W, pady=(10, 0))
        self.refresh_interval_var = tk.IntVar(value=5)
        ttk.Scale(basic_frame, from_=1, to=60, variable=self.refresh_interval_var, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 5))
        ttk.Label(basic_frame, textvariable=self.refresh_interval_var).pack(anchor=tk.W)

        # 监控设置
        ttk.Label(basic_frame, text="监控设置", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(20, 10))

        self.auto_start_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(basic_frame, text="启动时自动开始监控", variable=self.auto_start_var).pack(anchor=tk.W, pady=(0, 5))

        self.show_system_tray_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(basic_frame, text="显示系统托盘图标", variable=self.show_system_tray_var).pack(anchor=tk.W, pady=(0, 5))

        # 日志设置
        ttk.Label(basic_frame, text="日志设置", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(20, 10))

        self.enable_log_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(basic_frame, text="启用日志记录", variable=self.enable_log_var).pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(basic_frame, text="日志级别:").pack(anchor=tk.W)
        self.log_level_var = tk.StringVar(value="INFO")
        log_level_frame = ttk.Frame(basic_frame)
        log_level_frame.pack(fill=tk.X, pady=(0, 10))
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            ttk.Radiobutton(log_level_frame, text=level, variable=self.log_level_var, value=level).pack(side=tk.LEFT, padx=(0, 10))

    def create_strategy_settings(self):
        """创建策略设置页"""
        strategy_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(strategy_frame, text="策略设置")

        # 网格策略设置
        ttk.Label(strategy_frame, text="网格策略设置", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        # BIAS阈值设置
        ttk.Label(strategy_frame, text="BIAS阈值设置:").pack(anchor=tk.W, pady=(0, 5))

        bias_frame = ttk.Frame(strategy_frame)
        bias_frame.pack(fill=tk.X, pady=(0, 10))

        thresholds = [
            ("深坑区上限", -8),
            ("黄金区上限", -3),
            ("震荡区上限", 2),
            ("减持区上限", 5)
        ]

        self.bias_vars = {}
        for i, (name, default) in enumerate(thresholds):
            ttk.Label(bias_frame, text=f"{name}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.DoubleVar(value=default)
            self.bias_vars[name] = var
            ttk.Entry(bias_frame, textvariable=var, width=10).grid(row=i, column=1, padx=10, pady=2)

        # 目标仓位设置
        ttk.Label(strategy_frame, text="目标仓位设置 (%):", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(20, 10))

        position_frame = ttk.Frame(strategy_frame)
        position_frame.pack(fill=tk.X, pady=(0, 10))

        positions = [
            ("深坑区", 80),
            ("黄金区", 60),
            ("震荡区", 50),
            ("减持区", 30),
            ("逃亡区", 10)
        ]

        self.position_vars = {}
        for i, (name, default) in enumerate(positions):
            ttk.Label(position_frame, text=f"{name}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            var = tk.IntVar(value=default)
            self.position_vars[name] = var
            ttk.Entry(position_frame, textvariable=var, width=10).grid(row=i, column=1, padx=10, pady=2)

    def create_alert_settings(self):
        """创建提醒设置页"""
        alert_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(alert_frame, text="提醒设置")

        # 价格提醒
        ttk.Label(alert_frame, text="价格提醒设置", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        self.enable_price_alert_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(alert_frame, text="启用价格提醒", variable=self.enable_price_alert_var).pack(anchor=tk.W, pady=(0, 5))

        self.enable_sound_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(alert_frame, text="启用声音提醒", variable=self.enable_sound_var).pack(anchor=tk.W, pady=(0, 5))

        self.enable_system_notification_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(alert_frame, text="启用系统通知", variable=self.enable_system_notification_var).pack(anchor=tk.W, pady=(0, 10))

        # 提醒频率设置
        ttk.Label(alert_frame, text="提醒频率设置:").pack(anchor=tk.W, pady=(0, 5))

        frequency_frame = ttk.Frame(alert_frame)
        frequency_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(frequency_frame, text="同价位提醒间隔 (分钟):").pack(anchor=tk.W)
        self.alert_interval_var = tk.IntVar(value=60)
        ttk.Scale(frequency_frame, from_=1, to=1440, variable=self.alert_interval_var, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 5))
        ttk.Label(frequency_frame, textvariable=self.alert_interval_var).pack(anchor=tk.W)

        # 提醒历史
        ttk.Label(alert_frame, text="提醒历史设置", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(20, 10))

        ttk.Label(alert_frame, text="历史记录保留天数:").pack(anchor=tk.W, pady=(0, 5))
        self.history_days_var = tk.IntVar(value=7)
        ttk.Spinbox(alert_frame, from_=1, to=365, textvariable=self.history_days_var, width=10).pack(anchor=tk.W, pady=(0, 10))

        ttk.Button(alert_frame, text="清理历史记录", command=self.clear_alert_history).pack(anchor=tk.W)

    def create_trade_settings(self):
        """创建交易设置页"""
        trade_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(trade_frame, text="交易设置")

        # 交易服务设置
        ttk.Label(trade_frame, text="交易服务设置", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        self.enable_auto_trade_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(trade_frame, text="启用自动交易 (谨慎使用)", variable=self.enable_auto_trade_var).pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(trade_frame, text="账户ID:").pack(anchor=tk.W, pady=(10, 0))
        self.account_id_var = tk.StringVar()
        ttk.Entry(trade_frame, textvariable=self.account_id_var, width=30).pack(anchor=tk.W, pady=(0, 10))

        # 风控设置
        ttk.Label(trade_frame, text="风控设置", font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(20, 10))

        self.enable_risk_control_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(trade_frame, text="启用风险控制", variable=self.enable_risk_control_var).pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(trade_frame, text="单日最大交易次数:").pack(anchor=tk.W, pady=(0, 5))
        self.max_daily_trades_var = tk.IntVar(value=10)
        ttk.Spinbox(trade_frame, from_=1, to=100, textvariable=self.max_daily_trades_var, width=10).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(trade_frame, text="单次最大交易金额:").pack(anchor=tk.W, pady=(0, 5))
        self.max_single_amount_var = tk.DoubleVar(value=10000)
        ttk.Entry(trade_frame, textvariable=self.max_single_amount_var, width=15).pack(anchor=tk.W, pady=(0, 10))

    def save_settings(self):
        """保存设置"""
        try:
            # TODO: 实现设置保存逻辑
            messagebox.showinfo("成功", "设置已保存")
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {e}")

    def reset_settings(self):
        """重置默认设置"""
        if messagebox.askyesno("确认", "确定要重置所有设置到默认值吗？"):
            # TODO: 实现设置重置逻辑
            messagebox.showinfo("成功", "设置已重置")

    def clear_alert_history(self):
        """清理提醒历史"""
        if messagebox.askyesno("确认", "确定要清理提醒历史记录吗？"):
            try:
                cleared_count = alert_manager.clear_old_alerts(0)
                messagebox.showinfo("成功", f"已清理 {cleared_count} 条提醒记录")
            except Exception as e:
                messagebox.showerror("错误", f"清理失败: {e}")

class AnalysisWindow:
    """数据分析窗口"""

    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("数据分析")
        self.window.geometry("1000x700")
        self.window.transient(parent)

        self.create_widgets()

    def create_widgets(self):
        """创建组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建图表
        self.create_charts(main_frame)

    def create_charts(self, parent):
        """创建图表"""
        # 创建matplotlib图表
        self.fig = Figure(figsize=(12, 8), dpi=80)

        # 价格走势图
        self.ax1 = self.fig.add_subplot(221)
        self.ax1.set_title('ETF价格走势')
        self.ax1.set_xlabel('时间')
        self.ax1.set_ylabel('价格')
        self.ax1.grid(True)

        # BIAS指标图
        self.ax2 = self.fig.add_subplot(222)
        self.ax2.set_title('BIAS指标')
        self.ax2.set_xlabel('时间')
        self.ax2.set_ylabel('BIAS (%)')
        self.ax2.grid(True)

        # 仓位分布图
        self.ax3 = self.fig.add_subplot(223)
        self.ax3.set_title('仓位分布')
        self.ax3.set_xlabel('ETF')
        self.ax3.set_ylabel('仓位 (%)')

        # 盈亏分布图
        self.ax4 = self.fig.add_subplot(224)
        self.ax4.set_title('盈亏分布')
        self.ax4.set_xlabel('ETF')
        self.ax4.set_ylabel('盈亏 (¥)')

        # 创建canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 添加工具栏
        toolbar_frame = ttk.Frame(self.window)
        toolbar_frame.pack(fill=tk.X)

        ttk.Button(toolbar_frame, text="刷新数据", command=self.refresh_data).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(toolbar_frame, text="导出图表", command=self.export_chart).pack(side=tk.LEFT, padx=5, pady=5)

    def refresh_data(self):
        """刷新数据"""
        # TODO: 实现数据刷新逻辑
        messagebox.showinfo("提示", "数据刷新功能待实现")

    def export_chart(self):
        """导出图表"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG文件", "*.png"), ("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if filename:
            self.fig.savefig(filename)
            messagebox.showinfo("成功", f"图表已导出到: {filename}")