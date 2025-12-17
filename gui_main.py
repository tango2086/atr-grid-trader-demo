# gui_main.py - BIAS-ATR 网格交易GUI主界面
"""
基于tkinter的现代化桌面GUI应用：
- 实时ETF监控面板
- 价格提醒通知
- 交易功能界面
- 配置管理
- 数据可视化
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
from datetime import datetime
import queue
import json
import os

from data_manager import get_data_manager
from strategy import GridStrategy
from indicators import calculate_indicators
from price_alert import alert_manager
from trader import get_trader, HAS_TRADER
import config

class NotificationQueue:
    """通知队列管理"""
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, message, level="info"):
        self.queue.put((message, level))

    def get(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None

class GridTraderGUI:
    """BIAS-ATR网格交易主GUI"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BIAS-ATR 智能网格交易系统")
        self.root.geometry("1400x800")
        self.root.minsize(1200, 600)

        # 设置现代化样式
        self.setup_styles()

        # 核心组件
        self.data_manager = get_data_manager()
        self.strategy = GridStrategy()
        self.notif_queue = NotificationQueue()
        self.running = True

        # 数据存储
        self.etf_data = {}
        self.alerts_history = []
        self.last_update = None

        # 创建界面
        self.create_widgets()
        self.create_menu()

        # 启动后台线程
        self.start_background_threads()

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_styles(self):
        """设置现代化样式"""
        self.colors = {
            'bg_primary': '#2b2b2b',
            'bg_secondary': '#3c3c3c',
            'bg_accent': '#4a90e2',
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc',
            'success': '#27ae60',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'grid_buy': '#2ecc71',
            'grid_sell': '#e74c3c'
        }

        # 配置ttk样式
        style = ttk.Style()
        style.theme_use('clam')

        # 自定义样式
        style.configure('Header.TFrame', background=self.colors['bg_secondary'])
        style.configure('Card.TFrame', background=self.colors['bg_secondary'], relief='raised', borderwidth=1)
        style.configure('Dark.TLabel', background=self.colors['bg_secondary'], foreground=self.colors['text_primary'])
        style.configure('Success.TLabel', background=self.colors['bg_secondary'], foreground=self.colors['success'])
        style.configure('Danger.TLabel', background=self.colors['bg_secondary'], foreground=self.colors['danger'])
        style.configure('Modern.TButton', padding=(10, 8))

        # 设置主窗口背景
        self.root.configure(bg=self.colors['bg_primary'])

    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导入持仓", command=self.import_holdings)
        file_menu.add_command(label="导出数据", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)

        # 交易菜单
        trade_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        menubar.add_cascade(label="交易", menu=trade_menu)
        trade_menu.add_command(label="手动下单", command=self.show_trade_dialog)
        trade_menu.add_command(label="批量下单", command=self.show_batch_trade_dialog)
        trade_menu.add_command(label="交易记录", command=self.show_trade_history)

        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="策略回测", command=self.show_backtest_dialog)
        tools_menu.add_command(label="数据分析", command=self.show_analysis_dialog)
        tools_menu.add_command(label="提醒设置", command=self.show_alert_settings)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)

    def create_widgets(self):
        """创建主界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, style='Header.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 顶部信息栏
        self.create_header(main_frame)

        # 创建左右分栏
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # 左侧：ETF监控面板
        left_frame = ttk.Frame(paned_window, style='Header.TFrame')
        paned_window.add(left_frame, weight=3)
        self.create_etf_monitor(left_frame)

        # 右侧：操作面板
        right_frame = ttk.Frame(paned_window, style='Header.TFrame')
        paned_window.add(right_frame, weight=1)
        self.create_control_panel(right_frame)

        # 底部状态栏
        self.create_status_bar()

    def create_header(self, parent):
        """创建顶部信息栏"""
        header_frame = ttk.Frame(parent, style='Header.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # 左侧：标题和状态
        left_header = ttk.Frame(header_frame, style='Header.TFrame')
        left_header.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title_label = ttk.Label(left_header, text="🤖 BIAS-ATR 智能网格交易",
                               font=('Microsoft YaHei', 16, 'bold'), style='Dark.TLabel')
        title_label.pack(side=tk.LEFT, padx=(0, 20))

        # 数据源状态
        self.status_label = ttk.Label(left_header, text="数据源: --", style='Dark.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=(0, 20))

        # 更新时间
        self.update_time_label = ttk.Label(left_header, text="更新: --", style='Dark.TLabel')
        self.update_time_label.pack(side=tk.LEFT)

        # 右侧：控制按钮
        right_header = ttk.Frame(header_frame, style='Header.TFrame')
        right_header.pack(side=tk.RIGHT)

        ttk.Button(right_header, text="🔄 刷新", command=self.manual_refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_header, text="⚙️ 设置", command=self.show_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_header, text="🔔 提醒", command=self.show_alerts).pack(side=tk.LEFT, padx=5)

    def create_etf_monitor(self, parent):
        """创建ETF监控面板"""
        # 标题
        title_frame = ttk.Frame(parent, style='Card.TFrame')
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(title_frame, text="ETF 监控面板", font=('Microsoft YaHei', 14, 'bold'),
                 style='Dark.TLabel').pack(side=tk.LEFT, padx=10, pady=5)

        # 汇总卡片框架
        summary_frame = ttk.Frame(parent, style='Header.TFrame')
        summary_frame.pack(fill=tk.X, pady=(0, 10))

        self.create_summary_cards(summary_frame)

        # ETF表格
        table_frame = ttk.Frame(parent, style='Card.TFrame')
        table_frame.pack(fill=tk.BOTH, expand=True)

        # 创建Treeview
        columns = ('code', 'name', 'price', 'bias', 'status', 'position', 'value', 'orders', 'alerts')
        self.etf_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

        # 设置列标题和宽度
        column_configs = {
            'code': ('代码', 80),
            'name': ('名称', 120),
            'price': ('价格', 80),
            'bias': ('BIAS', 80),
            'status': ('状态', 120),
            'position': ('仓位', 80),
            'value': ('市值', 100),
            'orders': ('建议订单', 200),
            'alerts': ('提醒', 100)
        }

        for col, (text, width) in column_configs.items():
            self.etf_tree.heading(col, text=text)
            self.etf_tree.column(col, width=width, anchor=tk.CENTER)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.etf_tree.yview)
        self.etf_tree.configure(yscrollcommand=scrollbar.set)

        self.etf_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)

        # 绑定双击事件
        self.etf_tree.bind('<Double-1>', self.on_etf_double_click)

    def create_summary_cards(self, parent):
        """创建汇总卡片"""
        self.summary_vars = {
            'total_capital': tk.StringVar(value="¥--"),
            'total_value': tk.StringVar(value="¥--"),
            'available_cash': tk.StringVar(value="¥--"),
            'total_profit': tk.StringVar(value="¥--"),
            'position_pct': tk.StringVar(value="--%")
        }

        cards_info = [
            ('总资产', 'total_capital', 'card_primary'),
            ('持仓市值', 'total_value', 'card_success'),
            ('可用现金', 'available_cash', 'card_info'),
            ('总盈亏', 'total_profit', 'card_warning'),
            ('仓位比例', 'position_pct', 'card_danger')
        ]

        for i, (title, var_key, style) in enumerate(cards_info):
            card_frame = ttk.Frame(parent, style=f'{style}.TFrame')
            card_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

            title_label = ttk.Label(card_frame, text=title, font=('Microsoft YaHei', 10),
                                   style='Dark.TLabel')
            title_label.pack(anchor=tk.W, padx=10, pady=(10, 5))

            value_label = ttk.Label(card_frame, textvariable=self.summary_vars[var_key],
                                   font=('Microsoft YaHei', 16, 'bold'), style='Dark.TLabel')
            value_label.pack(anchor=tk.W, padx=10, pady=(0, 10))

    def create_control_panel(self, parent):
        """创建右侧控制面板"""
        # 价格提醒面板
        alert_frame = ttk.LabelFrame(parent, text="🔔 价格提醒", style='Card.TFrame')
        alert_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.alert_text = tk.Text(alert_frame, height=10, width=30,
                                  bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                  font=('Consolas', 9))
        alert_scrollbar = ttk.Scrollbar(alert_frame, orient=tk.VERTICAL, command=self.alert_text.yview)
        self.alert_text.configure(yscrollcommand=alert_scrollbar.set)

        self.alert_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        alert_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)

        # 快速操作面板
        action_frame = ttk.LabelFrame(parent, text="⚡ 快速操作", style='Card.TFrame')
        action_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        actions = [
            ("🔄 手动刷新", self.manual_refresh),
            ("💰 手动下单", self.show_trade_dialog),
            ("📊 数据分析", self.show_analysis_dialog),
            ("⚙️ 系统设置", self.show_settings),
            ("📈 策略回测", self.show_backtest_dialog),
            ("🔔 提醒历史", self.show_alerts)
        ]

        for i, (text, command) in enumerate(actions):
            btn = ttk.Button(action_frame, text=text, command=command, style='Modern.TButton')
            btn.pack(fill=tk.X, padx=10, pady=5)

        # 系统状态面板
        status_frame = ttk.LabelFrame(parent, text="🖥️ 系统状态", style='Card.TFrame')
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        self.system_status_text = tk.Text(status_frame, height=8, width=30,
                                         bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                         font=('Consolas', 9))
        self.system_status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def create_status_bar(self):
        """创建底部状态栏"""
        status_frame = ttk.Frame(self.root, style='Header.TFrame')
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # 左侧：状态信息
        self.status_text = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_text, style='Dark.TLabel').pack(side=tk.LEFT, padx=10, pady=5)

        # 右侧：连接状态
        self.connection_status = tk.StringVar(value="🟢 数据连接正常")
        ttk.Label(status_frame, textvariable=self.connection_status, style='Success.TLabel').pack(side=tk.RIGHT, padx=10, pady=5)

    def start_background_threads(self):
        """启动后台线程"""
        # 数据更新线程
        self.data_thread = threading.Thread(target=self.data_update_loop, daemon=True)
        self.data_thread.start()

        # 通知处理线程
        self.notif_thread = threading.Thread(target=self.notification_loop, daemon=True)
        self.notif_thread.start()

    def data_update_loop(self):
        """数据更新循环"""
        while self.running:
            try:
                self.update_data()
                time.sleep(5)  # 5秒更新一次
            except Exception as e:
                self.notif_queue.put(f"数据更新失败: {e}", "error")
                time.sleep(10)

    def notification_loop(self):
        """通知处理循环"""
        while self.running:
            notif = self.notif_queue.get()
            if notif:
                message, level = notif
                self.show_notification(message, level)
            time.sleep(0.5)

    def update_data(self):
        """更新数据"""
        try:
            total_value = 0
            total_profit = 0

            for code in config.ETF_LIST:
                # 获取数据
                df = self.data_manager.get_history(code, count=50)
                if df is None or df.empty:
                    continue

                # 计算指标
                df = calculate_indicators(df)

                # 获取持仓
                holdings = config.REAL_HOLDINGS.get(code, {
                    'volume': 0, 'available': 0, 'avg_cost': 0
                })

                # 策略分析
                plan = self.strategy.analyze(code, df, holdings)

                # 检测价格提醒
                orders_data = [
                    {
                        'direction': o.direction,
                        'price': o.price,
                        'amount': o.amount,
                        'desc': o.desc
                    } for o in plan.suggested_orders
                ]

                last = df.iloc[-1]
                current_price = float(last['close'])

                new_alerts = alert_manager.check_price_alerts(
                    code=code,
                    name=config.ETF_NAMES.get(code, code),
                    current_price=current_price,
                    suggested_orders=orders_data
                )

                # 添加提醒到队列
                for alert in new_alerts:
                    self.notif_queue.put(alert.message, "info")

                # 计算市值
                vol = holdings.get('volume', 0)
                cost = holdings.get('avg_cost', 0)
                market_value = current_price * vol
                total_value += market_value
                if cost > 0 and vol > 0:
                    total_profit += (current_price - cost) * vol

                # 更新ETF数据
                self.etf_data[code] = {
                    'code': code,
                    'name': config.ETF_NAMES.get(code, code),
                    'price': current_price,
                    'bias': float(plan.current_bias),
                    'status': plan.market_status,
                    'holdings': holdings,
                    'orders': plan.suggested_orders,
                    'warnings': plan.warnings,
                    'new_alerts': len(new_alerts)
                }

            # 更新界面
            self.root.after(0, self.update_ui, total_value, total_profit)

        except Exception as e:
            self.notif_queue.put(f"更新失败: {e}", "error")

    def update_ui(self, total_value, total_profit):
        """更新界面显示"""
        try:
            # 更新时间
            self.last_update = datetime.now()
            self.update_time_label.config(text=f"更新: {self.last_update.strftime('%H:%M:%S')}")

            # 更新汇总数据
            available_cash = config.TOTAL_CAPITAL - total_value
            self.summary_vars['total_capital'].set(f"¥{config.TOTAL_CAPITAL:,.0f}")
            self.summary_vars['total_value'].set(f"¥{total_value:,.0f}")
            self.summary_vars['available_cash'].set(f"¥{available_cash:,.0f}")
            self.summary_vars['total_profit'].set(f"{'+' if total_profit >= 0 else ''}¥{total_profit:,.0f}")
            self.summary_vars['position_pct'].set(f"{total_value/config.TOTAL_CAPITAL*100:.1f}%")

            # 更新ETF表格
            self.update_etf_tree()

            # 更新提醒文本
            self.update_alert_text()

            # 更新系统状态
            self.update_system_status()

        except Exception as e:
            print(f"UI更新错误: {e}")

    def update_etf_tree(self):
        """更新ETF表格"""
        # 清空现有数据
        for item in self.etf_tree.get_children():
            self.etf_tree.delete(item)

        # 添加新数据
        for code, data in self.etf_data.items():
            holdings = data['holdings']
            orders = data['orders']

            # 计算市值
            market_value = data['price'] * holdings.get('volume', 0)

            # 格式化订单信息
            order_info = []
            for order in orders[:2]:  # 只显示前2个订单
                direction_icon = "🔵" if order.direction == 'BUY' else "🔴"
                order_info.append(f"{direction_icon}{order.price:.3f}×{order.amount}")
            if len(orders) > 2:
                order_info.append(f"...+{len(orders)-2}")

            # 提醒信息
            alert_info = f"🔔{data['new_alerts']}" if data['new_alerts'] > 0 else ""

            # 插入数据
            self.etf_tree.insert('', tk.END, values=(
                code,
                data['name'],
                f"{data['price']:.3f}",
                f"{data['bias']:.2f}%",
                data['status'],
                f"{holdings.get('volume', 0)}",
                f"¥{market_value:,.0f}",
                ' '.join(order_info),
                alert_info
            ))

    def update_alert_text(self):
        """更新提醒文本"""
        try:
            # 获取最近的提醒
            recent_alerts = alert_manager.get_recent_alerts(hours=24)

            self.alert_text.delete(1.0, tk.END)

            if recent_alerts:
                for alert in recent_alerts[-10:]:  # 显示最近10条
                    time_str = alert.timestamp.strftime('%H:%M')
                    icon = "🔥" if alert.direction == 'BUY' else "💰"
                    self.alert_text.insert(tk.END, f"{time_str} {icon} {alert.message}\n\n")
            else:
                self.alert_text.insert(tk.END, "暂无价格提醒\n\n")

        except Exception as e:
            print(f"更新提醒文本错误: {e}")

    def update_system_status(self):
        """更新系统状态"""
        try:
            status_info = []

            # 数据源状态
            data_source = self.data_manager.get_data_source()
            status_info.append(f"📊 数据源: {data_source}")

            # 策略状态
            status_info.append(f"🤖 策略: 正常运行")

            # 提醒统计
            stats = alert_manager.get_alert_count(24)
            status_info.append(f"🔔 今日提醒: {stats['total']}次")

            # 交易状态
            if HAS_TRADER:
                trader = get_trader()
                conn_status = "已连接" if trader.is_connected() else "未连接"
                status_info.append(f"💼 交易: {conn_status}")
            else:
                status_info.append(f"💼 交易: 未启用")

            # ETF数量
            status_info.append(f"📈 监控ETF: {len(self.etf_data)}只")

            self.system_status_text.delete(1.0, tk.END)
            self.system_status_text.insert(tk.END, '\n'.join(status_info))

        except Exception as e:
            print(f"更新系统状态错误: {e}")

    def show_notification(self, message, level="info"):
        """显示通知"""
        def update():
            if level == "error":
                messagebox.showerror("错误", message)
            elif level == "warning":
                messagebox.showwarning("警告", message)
            else:
                # 简单的info通知，不打扰用户
                self.status_text.set(message)
                self.root.after(3000, lambda: self.status_text.set("就绪"))

        self.root.after(0, update)

    def manual_refresh(self):
        """手动刷新"""
        self.status_text.set("正在刷新数据...")
        threading.Thread(target=self.update_data, daemon=True).start()

    def on_etf_double_click(self, event):
        """ETF双击事件"""
        selection = self.etf_tree.selection()
        if selection:
            item = self.etf_tree.item(selection[0])
            code = item['values'][0]
            self.show_etf_detail(code)

    def show_etf_detail(self, code):
        """显示ETF详情"""
        # TODO: 实现ETF详情窗口
        messagebox.showinfo("ETF详情", f"ETF {code} 详情功能待实现")

    # 各种对话框方法（简单实现，实际可以扩展）
    def show_trade_dialog(self):
        """显示交易对话框"""
        messagebox.showinfo("手动下单", "交易对话框功能待实现")

    def show_batch_trade_dialog(self):
        """显示批量交易对话框"""
        messagebox.showinfo("批量下单", "批量交易功能待实现")

    def show_trade_history(self):
        """显示交易历史"""
        messagebox.showinfo("交易记录", "交易历史功能待实现")

    def show_backtest_dialog(self):
        """显示回测对话框"""
        messagebox.showinfo("策略回测", "策略回测功能待实现")

    def show_analysis_dialog(self):
        """显示数据分析对话框"""
        messagebox.showinfo("数据分析", "数据分析功能待实现")

    def show_alert_settings(self):
        """显示提醒设置对话框"""
        messagebox.showinfo("提醒设置", "提醒设置功能待实现")

    def show_settings(self):
        """显示设置对话框"""
        messagebox.showinfo("系统设置", "系统设置功能待实现")

    def show_alerts(self):
        """显示提醒历史"""
        messagebox.showinfo("提醒历史", "提醒历史功能待实现")

    def import_holdings(self):
        """导入持仓"""
        messagebox.showinfo("导入持仓", "导入持仓功能待实现")

    def export_data(self):
        """导出数据"""
        messagebox.showinfo("导出数据", "导出数据功能待实现")

    def show_help(self):
        """显示帮助"""
        help_text = """
BIAS-ATR 智能网格交易系统 v1.0

主要功能：
1. 实时ETF监控 - 显示实时价格、BIAS指标、网格建议
2. 价格提醒 - 当价格触及网格买卖点时自动提醒
3. 策略分析 - 基于BIAS和ATR的智能网格策略
4. 交易管理 - 支持手动下单和批量操作

使用说明：
1. 启动程序后会自动开始监控配置的ETF
2. 价格触及网格点时会收到提醒通知
3. 可以通过界面查看详细的市场状态和交易建议
4. 支持手动下单和系统设置配置

技术支持：
- 数据源：基于tushare或akshare
- 策略：BIAS-ATR网格交易策略
- 提醒：实时价格监控和通知
        """
        messagebox.showinfo("使用说明", help_text)

    def show_about(self):
        """显示关于信息"""
        about_text = """
BIAS-ATR 智能网格交易系统
版本: 1.0.0

一个基于BIAS和ATR指标的智能ETF网格交易系统
结合现代UI设计和实时价格提醒功能

开发者: AI Assistant
技术栈: Python + tkinter + pandas + numpy

版权所有 © 2024
        """
        messagebox.showinfo("关于", about_text)

    def on_closing(self):
        """关闭程序"""
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            self.running = False
            self.root.destroy()

    def run(self):
        """运行GUI"""
        self.root.mainloop()

def main():
    """主函数"""
    app = GridTraderGUI()
    app.run()

if __name__ == "__main__":
    main()