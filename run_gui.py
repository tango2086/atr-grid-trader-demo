# run_gui.py - GUI启动脚本
"""
BIAS-ATR 智能网格交易系统 GUI
支持演示模式和真实数据模式
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
from datetime import datetime
import random
from typing import Dict, List, Optional

# 项目模块导入
import config
from data_manager import get_data_manager
from strategy import GridStrategy, TradePlan
from holdings_storage import init_holdings_from_local, load_holdings
from price_alert import alert_manager
from logger import get_logger
from indicators import calculate_indicators
from gui_dialogs import TradeDialog
from gui_components import StockChart, GridVizPanel, StatusDashboard


class GUIConfig:
    """GUI配置类"""
    # 从 config.py 读取
    ETF_LIST = config.ETF_LIST
    ETF_NAMES = config.ETF_NAMES
    REAL_HOLDINGS = config.REAL_HOLDINGS
    TOTAL_CAPITAL = config.TOTAL_CAPITAL
    
    # GUI特定配置
    UPDATE_INTERVAL = 3000  # 毫秒
    WINDOW_SIZE = "1400x800"
    MIN_SIZE = (1200, 600)
    THEME = "dark"


class GridTraderGUI:
    """BIAS-ATR 智能网格交易系统 GUI"""

    def __init__(self, mode='demo'):
        """
        初始化GUI
        
        Args:
            mode: 'demo' 演示模式 | 'real' 真实模式
        """
        self.mode = mode
        self.config = GUIConfig()
        
        # 核心组件
        self.data_manager = get_data_manager()
        self.strategy = GridStrategy()
        self.logger = get_logger()
        
        # 数据和状态
        self.etf_data: Dict = {}
        self.data_lock = threading.Lock()  # 线程安全
        self.running = True
        self.last_update = None
        
        # 初始化持仓
        init_holdings_from_local()
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title(f"BIAS-ATR 智能网格交易系统 ({'演示模式' if mode == 'demo' else '真实模式'})")
        self.root.geometry(self.config.WINDOW_SIZE)
        self.root.minsize(*self.config.MIN_SIZE)

        # 设置现代化样式
        self.setup_styles()

        # 创建界面
        self.create_widgets()
        self.create_menu()

        # 启动后台更新
        self.start_simulation()

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 记录启动
        self.logger.info(f"GUI启动 - 模式: {mode}", "GUI")
    
    @staticmethod
    def get_market_status(bias: float) -> str:
        """
        根据BIAS值判断市场状态
        
        Args:
            bias: BIAS指标值
            
        Returns:
            市场状态描述
        """
        if bias < config.BIAS_THRESHOLDS.DEEP_DIP:
            return "DEEP_DIP (深坑)"
        elif bias < config.BIAS_THRESHOLDS.GOLD_ZONE_UPPER:
            return "GOLD_ZONE (黄金)"
        elif bias < config.BIAS_THRESHOLDS.OSCILLATION_UPPER:
            return "OSCILLATION (震荡)"
        elif bias < config.BIAS_THRESHOLDS.REDUCE_ZONE_UPPER:
            return "REDUCE_ZONE (减持)"
        else:
            return "ESCAPE_ZONE (逃亡)"

    def setup_styles(self):
        """设置现代化样式 (Dark Mode)"""
        self.colors = {
            'bg_primary': '#121212',      # 深黑背景
            'bg_secondary': '#1E1E1E',    # 卡片背景
            'bg_selected': '#2C2C2C',     # 选中背景
            'text_primary': '#E0E0E0',    # 主文本
            'text_secondary': '#A0A0A0',  # 次要文本
            'accent': '#6366f1',          # 强调色 (Indigo)
            'success': '#10b981',         # 成功 (Emerald)
            'danger': '#ef4444',          # 危险 (Red)
            'warning': '#f59e0b',         # 警告 (Amber)
            'info': '#3b82f6',            # 信息 (Blue)
            'border': '#333333'           # 边框颜色
        }

        # 配置ttk样式
        style = ttk.Style()
        style.theme_use('clam')

        # 通用配置
        style.configure('.', 
            background=self.colors['bg_primary'], 
            foreground=self.colors['text_primary'], 
            borderwidth=0,
            font=('Microsoft YaHei', 10)
        )

        # 框架样式
        style.configure('Main.TFrame', background=self.colors['bg_primary'])
        style.configure('Card.TFrame', background=self.colors['bg_secondary']) # 去除边框，只用背景色
        
        # 标签样式
        style.configure('CardTitle.TLabel', 
            background=self.colors['bg_secondary'], 
            foreground=self.colors['text_secondary'],
            font=('Microsoft YaHei', 9)
        )
        style.configure('CardValue.TLabel', 
            background=self.colors['bg_secondary'], 
            foreground=self.colors['text_primary'],
            font=('DIN Alternate', 20, 'bold') # 使用数字字体
        )
        style.configure('Dark.TLabel', background=self.colors['bg_secondary'], foreground=self.colors['text_primary'])
        style.configure('Status.TLabel', background=self.colors['bg_primary'], foreground=self.colors['text_secondary'], font=('Consolas', 9))

        # 按钮样式
        style.configure('Action.TButton', 
            background=self.colors['bg_secondary'], 
            foreground=self.colors['text_primary'],
            borderwidth=0,
            focuscolor=self.colors['bg_selected']
        )
        style.map('Action.TButton',
            background=[('active', self.colors['bg_selected'])],
            foreground=[('active', '#ffffff')]
        )
        
        # 树形列表样式 (Treeview)
        style.configure('Treeview',
            background=self.colors['bg_primary'],
            foreground=self.colors['text_primary'],
            fieldbackground=self.colors['bg_primary'],
            rowheight=32,  # 增加行高
            font=('Microsoft YaHei', 11),
            borderwidth=0
        )
        style.configure('Treeview.Heading',
            background=self.colors['bg_primary'],
            foreground=self.colors['text_secondary'],
            font=('Microsoft YaHei', 9),
            borderwidth=0
        )
        style.map('Treeview',
            background=[('selected', self.colors['bg_selected'])],
            foreground=[('selected', self.colors['text_primary'])]
        )
        
        # 配置Treeview Tag样式
        self.etf_tree_tags_configured = False # 标记是否已配置

        # 设置主窗口背景
        self.root.configure(bg=self.colors['bg_primary'])

    def generate_mock_data(self):
        """
        生成/更新ETF数据
        使用真实的数据管理器和策略引擎
        """
        try:
            data = {}
            
            with self.data_lock:
                for code in self.config.ETF_LIST:
                    try:
                        # 获取历史数据
                        df = self.data_manager.get_history(code, count=100, use_cache=True)
                        if df.empty:
                            self.logger.warning(f"无法获取 {code} 的数据", "GUI")
                            continue
                        
                        # 计算指标
                        df = calculate_indicators(df)
                        
                        # 获取持仓信息
                        holdings = self.config.REAL_HOLDINGS.get(code, {
                            'volume': 0,
                            'avg_cost': 0,
                            'available': 0
                        })
                        
                        # 策略分析
                        plan = self.strategy.analyze(code, df, holdings)
                        
                        # 检查价格提醒
                        etf_name = self.config.ETF_NAMES.get(code, code)
                        alerts = alert_manager.check_price_alerts(
                            code,
                            etf_name,
                            plan.current_price,
                            [{'direction': o.direction, 'price': o.price, 'amount': o.amount} 
                             for o in plan.suggested_orders]
                        )
                        
                        # 存储数据
                        data[code] = {
                            'code': code,
                            'name': etf_name,
                            'price': plan.current_price,
                            'bias': plan.current_bias,
                            'status': plan.market_status,
                            'holdings': holdings,
                            'orders': plan.suggested_orders,
                            'warnings': plan.warnings,
                            'new_alerts': len(alerts),
                            'plan': plan,  # 保存完整的TradePlan对象
                            'df': df  # 保存DataFrame用于后续分析
                        }
                        
                    except Exception as e:
                        self.logger.error(f"处理 {code} 数据失败: {e}", "GUI")
                        continue
            
            return data
            
        except Exception as e:
            self.logger.error(f"生成数据失败: {e}", "GUI", exc=e)
            return {}

    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导出数据", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)

        # 交易菜单
        trade_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        menubar.add_cascade(label="交易", menu=trade_menu)
        trade_menu.add_command(label="手动下单", command=self.show_trade_dialog)
        trade_menu.add_command(label="模拟交易", command=self.simulate_trade)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)

    def create_widgets(self):
        """创建主界面组件 (左-中-右 布局)"""
        # 顶部：核心资产栏
        self.create_top_panel()

        # 主内容区域 (三栏结构)
        # 使用 PanedWindow 允许调整大小
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 1. 左侧：监控列表 (20%)
        self.left_panel = ttk.Frame(self.main_paned, style='Main.TFrame')
        self.main_paned.add(self.left_panel, weight=1)
        self.create_left_panel(self.left_panel)

        # 2. 中间：核心可视化区 (60%)
        self.middle_panel = ttk.Frame(self.main_paned, style='Main.TFrame')
        self.main_paned.add(self.middle_panel, weight=4)
        self.create_middle_panel(self.middle_panel)

        # 3. 右侧：操作与日志 (20%)
        self.right_panel = ttk.Frame(self.main_paned, style='Main.TFrame')
        self.main_paned.add(self.right_panel, weight=1)
        self.create_right_panel(self.right_panel)

        # 底部状态栏
        self.create_status_bar()

    def create_top_panel(self):
        """创建顶部核心资产栏"""
        top_frame = ttk.Frame(self.root, style='Main.TFrame')
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        # 初始化变量
        self.summary_vars = {
            'total_asset': tk.StringVar(value="--"),
            'day_pnl': tk.StringVar(value="--"),
            'pos_pct': tk.DoubleVar(value=0),
            'pos_text': tk.StringVar(value="--%")
        }

        # 卡片布局
        cards = [
            ("总资产", self.summary_vars['total_asset'], None),
            ("今日盈亏", self.summary_vars['day_pnl'], "pnl"), # 特殊处理颜色
            ("仓位比例", self.summary_vars['pos_text'], "progress") # 特殊处理进度条
        ]

        for title, var, type_ in cards:
            card = ttk.Frame(top_frame, style='Card.TFrame', padding=15)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
            
            # 标题
            ttk.Label(card, text=title, style='CardTitle.TLabel').pack(anchor=tk.W)
            
            # 数值
            if type_ == 'pnl':
                self.pnl_label = ttk.Label(card, textvariable=var, style='CardValue.TLabel')
                self.pnl_label.pack(anchor=tk.W, pady=(5,0))
            else:
                ttk.Label(card, textvariable=var, style='CardValue.TLabel').pack(anchor=tk.W, pady=(5,0))
            
        # 进度条 (仅仓位卡片)
            if type_ == 'progress':
                # 定义不同颜色的进度条样式
                style = ttk.Style()
                style.configure("Safe.Horizontal.TProgressbar", foreground='#10b981', background='#10b981')
                style.configure("Warn.Horizontal.TProgressbar", foreground='#f59e0b', background='#f59e0b')
                
                self.pos_progress = ttk.Progressbar(card, orient=tk.HORIZONTAL, length=100, mode='determinate', 
                                                  variable=self.summary_vars['pos_pct'], style="Safe.Horizontal.TProgressbar")
                self.pos_progress.pack(fill=tk.X, pady=(10, 0))

        # 顶部右侧：全局操作
        action_frame = ttk.Frame(top_frame, style='Main.TFrame')
        action_frame.pack(side=tk.RIGHT)
        
        ttk.Button(action_frame, text="🔄 刷新", style='Action.TButton', command=self.manual_refresh).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="⚙️ 设置", style='Action.TButton', command=lambda: messagebox.showinfo("提示", "设置功能开发中")).pack(side=tk.RIGHT, padx=5)

    def create_left_panel(self, parent):
        """创建左侧监控列表"""
        # 标题
        ttk.Label(parent, text="监控列表", style='Status.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        # 列表容器 (带圆角背景)
        list_frame = ttk.Frame(parent, style='Card.TFrame', padding=1)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview (简化列)
        columns = ('code', 'info', 'price', 'atr') # info包含名称和状态
        self.etf_tree = ttk.Treeview(list_frame, columns=columns, show='', selectmode='browse')
        
        # 列宽设置
        self.etf_tree.column('code', width=60, anchor=tk.W)
        self.etf_tree.column('info', width=100, anchor=tk.W)
        self.etf_tree.column('price', width=80, anchor=tk.E)
        self.etf_tree.column('atr', width=60, anchor=tk.E)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.etf_tree.yview)
        self.etf_tree.configure(yscrollcommand=scrollbar.set)
        
        self.etf_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定点击事件
        self.etf_tree.bind('<<TreeviewSelect>>', self.on_etf_select)

    def create_middle_panel(self, parent):
        """创建中间核心可视化区"""
        # 图表区域
        self.chart_frame = ttk.Frame(parent, style='Card.TFrame')
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=0)
        
        self.stock_chart = StockChart(self.chart_frame)
        self.stock_chart.pack(fill=tk.BOTH, expand=True)
        
        # 底部：网格交易可视化
        self.grid_viz = GridVizPanel(parent)
        self.grid_viz.pack(fill=tk.X, padx=5, pady=(10, 0))
        
    def create_right_panel(self, parent):
        """创建右侧操作区"""
        # 1. 快速交易
        trade_frame = ttk.Frame(parent, style='Card.TFrame', padding=15)
        trade_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(trade_frame, text="快速交易", style='CardTitle.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        # 当前选中ETF
        self.selected_etf_var = tk.StringVar(value="未选择")
        ttk.Label(trade_frame, textvariable=self.selected_etf_var, style='Dark.TLabel', font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        btn_grid = ttk.Frame(trade_frame, style='Card.TFrame')
        btn_grid.pack(fill=tk.X)
        
        # 买卖按钮
        self.btn_buy = tk.Button(btn_grid, text="买入", bg=self.colors['success'], fg='white', relief='flat', font=('Microsoft YaHei', 10, 'bold'), command=lambda: self.quick_trade('BUY'))
        self.btn_buy.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), pady=5)
        
        self.btn_sell = tk.Button(btn_grid, text="卖出", bg=self.colors['danger'], fg='white', relief='flat', font=('Microsoft YaHei', 10, 'bold'), command=lambda: self.quick_trade('SELL'))
        self.btn_sell.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0), pady=5)

        # 2. 系统状态
        self.status_dashboard = StatusDashboard(parent)
        self.status_dashboard.pack(fill=tk.X, pady=(0, 10))

        # 3. 系统日志
        log_frame = ttk.Frame(parent, style='Card.TFrame', padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(log_frame, text="运行日志", style='CardTitle.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        self.log_text = tk.Text(log_frame, bg=self.colors['bg_primary'], fg=self.colors['text_secondary'], 
                               font=('Consolas', 8), relief='flat', height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def on_etf_select(self, event):
        """左侧列表选择事件"""
        selection = self.etf_tree.selection()
        if not selection:
            return

        try:
            # 获取选中的code
            item = self.etf_tree.item(selection[0])
            code = item['values'][0]
            
            # 更新选中状态变量
            self.selected_etf_var.set(f"{config.ETF_NAMES.get(code, code)} ({code})")
            
            # 获取数据
            with self.data_lock:
                data = self.etf_data.get(code)
            
            if data:
                # 1. 更新中间图表
                # 注意：这里假设data['df']存在。如果是真实模式，需要确保data_manager保留了df
                # 如果是模拟模式，generate_mock_data需要保存df
                df = data.get('df') 
                orders = data.get('orders', [])
                current_price = data.get('price')
                holdings = data.get('holdings', {})  # [NEW] 传递持仓信息用于显示成本线
                
                self.stock_chart.plot_data(df, orders, current_price, holdings=holdings)
                
                # 2. 更新底部网格可视化
                # 构造简单的grid_info模拟
                grid_info = {
                    'lower': current_price * 0.95, # 模拟，实际应从策略获取
                    'upper': current_price * 1.05
                }
                self.grid_viz.update_data(current_price, orders, grid_info)
                
        except Exception as e:
            self.logger.error(f"选择ETF出错: {e}", "GUI")

    def quick_trade(self, direction):
        """快速交易响应"""
        selection = self.etf_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先在左侧选择一个ETF")
            return

        # 获取当前选中的ETF信息
        item = self.etf_tree.item(selection[0])
        code = item['values'][0]
        name = config.ETF_NAMES.get(code, code)
        
        # 二次确认 (Safety)
        action_text = "买入" if direction == 'BUY' else "卖出"
        if not messagebox.askyesno("确认交易", f"确定要【{action_text}】 {name} ({code}) 吗？\n\n这将打开交易对话框。"):
            return
        
        # 调用 TradeDialog (复用现有逻辑)
        self.show_trade_dialog()

    # create_header 已被 create_top_panel 替代

    # create_etf_monitor 已被 create_left_panel 替代

    # create_summary_cards 已被 create_top_panel 替代

    # create_control_panel 已被 create_right_panel 替代

    def create_status_bar(self):
        """创建底部状态栏"""
        status_frame = ttk.Frame(self.root, style='Header.TFrame')
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # 左侧：状态信息
        self.status_text = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_text, style='Dark.TLabel').pack(side=tk.LEFT, padx=10, pady=5)

        # 右侧：连接状态
        self.connection_status = tk.StringVar(value="🟡 演示模式运行中")
        ttk.Label(status_frame, textvariable=self.connection_status, style='Warning.TLabel').pack(side=tk.RIGHT, padx=10, pady=5)

    def start_simulation(self):
        """启动模拟线程"""
        self.simulation_thread = threading.Thread(target=self.simulation_loop, daemon=True)
        self.simulation_thread.start()

    def simulation_loop(self):
        """数据更新循环"""
        while self.running:
            try:
                self.simulate_data_update()
                time.sleep(self.config.UPDATE_INTERVAL / 1000)  # 转换为秒
            except Exception as e:
                self.logger.error(f"数据更新循环错误: {e}", "GUI", exc=e)
                time.sleep(5)

    def simulate_data_update(self):
        """更新数据"""
        try:
            # 重新生成/更新数据
            new_data = self.generate_mock_data()
            
            # 线程安全地更新数据
            with self.data_lock:
                self.etf_data = new_data
            
            # 更新界面
            self.root.after(0, self.update_ui)
            
        except Exception as e:
            self.logger.error(f"数据更新失败: {e}", "GUI", exc=e)

    def update_ui(self):
        """更新界面显示"""
        try:
            # 更新时间
            self.last_update = datetime.now()
            # self.update_time_label.config(text=f"更新: {self.last_update.strftime('%H:%M:%S')}") # 已移除

            # 计算汇总数据
            total_value = 0
            total_profit = 0
            today_pnl = 0 # 需从数据源获取，暂模拟

            with self.data_lock:
                for code, data in self.etf_data.items():
                    holdings = data['holdings']
                    market_value = data['price'] * holdings.get('volume', 0)
                    total_value += market_value

                    cost = holdings.get('avg_cost', data['price'])
                    if cost > 0 and holdings.get('volume', 0) > 0:
                        profit = (data['price'] - cost) * holdings.get('volume', 0)
                        total_profit += profit
                        # 简单模拟今日盈亏 (实际应从交易记录算)
                        today_pnl += profit * 0.1 # 假定变动 

            # [FIX] 获取已实现盈亏，使总资产计算与Web一致
            from persistence import grid_state_manager
            all_time_realized_pnl = grid_state_manager.get_realized_pnl()
            today_realized_pnl = grid_state_manager.get_realized_pnl(start_date=datetime.now().strftime('%Y-%m-%d'))
            
            # 总盈亏 = 浮盈 + 已实现盈亏
            final_total_profit = total_profit + all_time_realized_pnl

            # 更新顶部卡片
            total_asset = self.config.TOTAL_CAPITAL + final_total_profit
            pos_pct = (total_value / total_asset * 100) if total_asset > 0 else 0
            
            self.summary_vars['total_asset'].set(f"¥{total_asset:,.0f}")
            self.summary_vars['day_pnl'].set(f"{'+' if today_realized_pnl >= 0 else ''}¥{today_realized_pnl:,.0f}")  # [FIX] 使用今日已实现盈亏
            self.summary_vars['pos_pct'].set(pos_pct)
            self.summary_vars['pos_text'].set(f"{pos_pct:.1f}%")
            
            # 更新进度条颜色
            if pos_pct > 80:
                self.pos_progress.configure(style="Warn.Horizontal.TProgressbar")
            else:
                self.pos_progress.configure(style="Safe.Horizontal.TProgressbar")

            # 设置盈亏颜色
            if total_profit >= 0:
                self.pnl_label.configure(foreground=self.colors['danger']) # A股红涨
            else:
                self.pnl_label.configure(foreground=self.colors['success']) # A股绿跌

            # 更新左侧列表
            self.update_left_panel()

            # 更新右侧日志
            self.update_logs()

            # 更新底部状态栏
            self.connection_status.set(f"📊 {len(self.etf_data)}只监控中 | {'🟢' if self.mode=='real' else '🟡'} {'实盘' if self.mode=='real' else '演示'}")

            # 更新右侧仪表盘
            if hasattr(self, 'status_dashboard'):
                mode_text = "实盘交易" if self.mode=='real' else "演示模式"
                self.status_dashboard.draw_status(True, mode_text)
                # 统计今日触发 (简单计算new_alerts总和)
                total_alerts = sum(d['new_alerts'] for d in self.etf_data.values())
                self.status_dashboard.update_stats(total_alerts, len(self.etf_data))

        except Exception as e:
            print(f"UI更新错误: {e}")
            import traceback
            traceback.print_exc()

    def update_left_panel(self):
        """更新左侧监控列表"""
        # 简单起见，全量刷新 (可优化为增量更新)
        # 记录当前选中
        selection = self.etf_tree.selection()
        selected_code = self.etf_tree.item(selection[0])['values'][0] if selection else None

        # 清空
        for item in self.etf_tree.get_children():
            self.etf_tree.delete(item)

        with self.data_lock:
            for code, data in self.etf_data.items():
                # Info: 名称 + 状态图标
                status_icon = "🟢" if "DIP" in data['status'] else "🔴" if "ESCAPE" in data['status'] else "⚪"
                info_text = f"{status_icon} {data['name']}"
                
                # Price
                price_text = f"{data['price']:.3f}"
                
                # ATR (从df获取)
                atr_val = 0
                if 'df' in data and not data['df'].empty and 'atr_14' in data['df'].columns:
                    atr_val = data['df']['atr_14'].iloc[-1]
                
                atr_text = f"{atr_val:.3f}"
                
                # 插入 (带tags)
                # 根据状态设置颜色
                tag = 'normal'
                if "DIP" in data['status']: tag = 'buy'
                elif "ESCAPE" in data['status']: tag = 'sell'
                
                # ATR预警Tag
                atr_tag = 'normal'
                atr_pct = (atr_val / data['price']) * 100 if data['price'] > 0 else 0
                if atr_pct < 0.5: atr_tag = 'low_vol'
                elif atr_pct > 3.0: atr_tag = 'high_vol'
                
                item_id = self.etf_tree.insert('', tk.END, values=(code, info_text, price_text, atr_text), tags=(tag, atr_tag))
                
                # 恢复选中
                if code == selected_code:
                    self.etf_tree.selection_set(item_id)
        
        # 配置tags颜色 (只运行一次)
        if not hasattr(self, 'etf_tree_tags_configured') or not self.etf_tree_tags_configured:
            self.etf_tree.tag_configure('buy', foreground=self.colors['success'])
            self.etf_tree.tag_configure('sell', foreground=self.colors['danger'])
            self.etf_tree.tag_configure('normal', foreground=self.colors['text_primary'])
            self.etf_tree.tag_configure('low_vol', foreground='#777777') # 低波动灰暗
            self.etf_tree.tag_configure('high_vol', foreground='#f59e0b') # 高波动橙色
            self.etf_tree_tags_configured = True

    def update_logs(self):
        """更新日志面板"""
        try:
            # 仅在有新内容时更新，避免闪烁
            # 这里简单实现：获取通过 logger 或 alert_manager 的最新消息
            alerts = alert_manager.get_recent_alerts(hours=1)
            
            self.log_text.delete(1.0, tk.END)
            for alert in alerts[:20]: # 显示最近20条
                 time_str = alert.timestamp.strftime('%H:%M')
                 # [FIX] 添加目标价和数量显示，与Web一致
                 target_price = getattr(alert, 'target_price', 0) or 0
                 amount = getattr(alert, 'amount', 0) or 0
                 direction = getattr(alert, 'direction', '')
                 name = getattr(alert, 'name', '')
                 
                 if target_price > 0 and amount > 0:
                     msg = f"[{time_str}] {name} {direction}: ¥{target_price:.3f} × {amount}股\n"
                 else:
                     msg = f"[{time_str}] {name}: {getattr(alert, 'message', '')}\n"
                 self.log_text.insert(tk.END, msg)
                 
                 # 简单高亮
                 if "买入" in msg:
                     # self._highlight(msg, 'red') # TODO
                     pass
                     
        except Exception as e:
            print(f"日志更新错误: {e}")

    # update_alert_text 已被 update_logs 替代
    # update_system_status 已移除，合并到底部状态栏

        except Exception as e:
            self.logger.error(f"更新提醒文本错误: {e}", "GUI")

    def update_system_status(self):
        """更新系统状态"""
        try:
            status_lines = [
                f"📊 数据源: {self.data_manager.get_data_source()}",
                f"🔌 连接状态: {'✅ 已连接' if self.data_manager.is_connected() else '⚠️ 模拟模式'}",
                f"🤖 策略: 网格交易",
                f"🔔 提醒: {alert_manager.get_alert_count(hours=24)}次/24h",
                f"💼 持仓: {len([h for h in self.config.REAL_HOLDINGS.values() if h.get('volume', 0) > 0])}只",
                f"📈 监控: {len(self.config.ETF_LIST)}只ETF",
                f"⏰ 更新: {datetime.now().strftime('%H:%M:%S')}"
            ]

            self.system_status_text.delete(1.0, tk.END)
            self.system_status_text.insert(tk.END, '\n'.join(status_lines))

        except Exception as e:
            self.logger.error(f"更新系统状态错误: {e}", "GUI")

    def manual_refresh(self):
        """手动刷新"""
        self.status_text.set("正在刷新数据...")
        self.generate_new_data()
        self.root.after(1000, lambda: self.status_text.set("就绪"))

    def generate_new_data(self):
        """生成新的模拟数据"""
        self.etf_data = self.generate_mock_data()
        self.update_ui()
        self.status_text.set("数据已更新")

    def on_etf_double_click(self, event):
        """ETF双击事件"""
        selection = self.etf_tree.selection()
        if selection:
            item = self.etf_tree.item(selection[0])
            code = item['values'][0]
            self.show_etf_detail(code)

    def show_etf_detail(self, code):
        """显示ETF详情 - [增强版] 与Web UI一致"""
        if code in self.etf_data:
            data = self.etf_data[code]
            holdings = data['holdings']
            
            # 计算浮盈
            floating_pnl = 0
            if holdings.get('volume', 0) > 0 and holdings.get('avg_cost', 0) > 0:
                floating_pnl = (data['price'] - holdings['avg_cost']) * holdings['volume']
            
            # 获取 ATR
            atr_val = 0
            if 'df' in data and not data['df'].empty and 'atr_14' in data['df'].columns:
                atr_val = data['df']['atr_14'].iloc[-1]
            
            # 从建议订单中提取支撑/阻力位
            support_levels = []
            resistance_levels = []
            for order in data.get('orders', []):
                price = order.price if hasattr(order, 'price') else order.get('price', 0)
                direction = order.direction if hasattr(order, 'direction') else order.get('direction', '')
                if direction == 'BUY':
                    support_levels.append(price)
                elif direction == 'SELL':
                    resistance_levels.append(price)
            
            # 构建详情信息
            detail_msg = f"""
═══════════════════════════════════
       {data['name']} ({code})
═══════════════════════════════════

【基本信息】
  当前价格: ¥{data['price']:.3f}
  BIAS指标: {data['bias']:.2f}%
  ATR(14):  ¥{atr_val:.4f}
  市场状态: {data['status']}

【持仓信息】
  持仓数量: {holdings.get('volume', 0):,}股
  平均成本: ¥{holdings.get('avg_cost', 0):.3f}
  可用数量: {holdings.get('available', 0):,}股
  浮动盈亏: {'+'if floating_pnl >= 0 else ''}¥{floating_pnl:,.2f}

【关键价位】
  支撑位: {', '.join([f'¥{p:.3f}' for p in sorted(support_levels)[:3]]) or '无'}
  阻力位: {', '.join([f'¥{p:.3f}' for p in sorted(resistance_levels)[:3]]) or '无'}

【建议订单】
"""
            # 处理订单
            for order in data['orders']:
                if hasattr(order, 'direction'):
                    direction = "🟢买入" if order.direction == 'BUY' else "🔴卖出"
                    detail_msg += f"  {direction}: ¥{order.price:.3f} × {order.amount}股"
                    if hasattr(order, 'desc') and order.desc:
                        detail_msg += f" ({order.desc})"
                    detail_msg += "\n"
                else:
                    direction = "🟢买入" if order.get('direction') == 'BUY' else "🔴卖出"
                    detail_msg += f"  {direction}: ¥{order.get('price', 0):.3f} × {order.get('amount', 0)}股"
                    if order.get('desc'):
                        detail_msg += f" ({order['desc']})"
                    detail_msg += "\n"

            messagebox.showinfo(f"ETF详情 - {data['name']}", detail_msg)

    def show_trade_dialog(self):
        """显示交易对话框"""
        if self.mode == 'demo':
            messagebox.showinfo("演示模式", "这是演示模式，无法执行真实交易。\n请使用 '--mode real' 参数启动程序。")
            return

        try:
            # 确保有数据
            if not self.etf_data:
                messagebox.showwarning("提示", "正在等待数据更新，请稍候...")
                return
            
            # 打开交易对话框
            TradeDialog(self.root, self.etf_data)
            
        except Exception as e:
            self.logger.error(f"打开交易对话框失败: {e}", "GUI")
            messagebox.showerror("错误", f"打开交易功能失败: {e}")

    def simulate_trade(self):
        """模拟交易"""
        result = messagebox.askyesno("模拟交易", "是否执行一次模拟交易？")
        if result:
            messagebox.showinfo("交易成功", """
模拟交易已成功执行！

📋 交易详情：
ETF: 沪深300ETF (510300)
方向: 买入
价格: ¥3.456
数量: 1000股
金额: ¥3,456.00

⚠️ 这是演示交易，非真实交易
            """)

    def test_alert(self):
        """测试提醒"""
        current_time = datetime.now().strftime('%H:%M:%S')
        messagebox.showwarning("价格提醒测试", f"""
🔥 买入提醒测试！

时间: {current_time}
ETF: 沪深300ETF (510300)
当前价: ¥3.456
目标价: ¥3.450
差价: -¥0.006

价格已触及买1点位，建议关注！

这是提醒功能演示
        """)

    def export_data(self):
        """导出数据"""
        filename = f"grid_trader_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        export_data = {
            'timestamp': datetime.now().isoformat(),
            'etf_data': self.etf_data,
            'summary': {
                'total_capital': 200000,
                'total_value': sum(data['price'] * data['holdings'].get('volume', 0) for data in self.etf_data.values())
            }
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            messagebox.showinfo("导出成功", f"数据已导出到:\n{filename}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出数据时出错:\n{e}")

    def show_about(self):
        """显示关于信息"""
        about_text = """
BIAS-ATR 智能网格交易系统 (演示版)
版本: 1.0.0 Demo

一个基于BIAS和ATR指标的智能ETF网格交易系统
结合现代UI设计和实时价格提醒功能

主要特性：
• 🤖 智能网格策略
• 📊 实时数据监控
• 🔔 价格提醒通知
• 💰 风险控制管理
• 📈 数据分析功能

开发者: AI Assistant
技术栈: Python + tkinter

🎯 这是一个功能演示版本
📝 实际使用需要连接真实数据源和交易接口

版权所有 © 2024
        """
        messagebox.showinfo("关于", about_text)

    def on_closing(self):
        """关闭程序"""
        if messagebox.askokcancel("退出", "确定要退出演示程序吗？"):
            self.running = False
            self.root.destroy()

    def run(self):
        """运行GUI"""
        self.root.mainloop()

def main():
    """主函数"""
    import sys
    
    # 解析命令行参数
    mode = 'demo'
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--mode', '-m']:
            mode = sys.argv[2] if len(sys.argv) > 2 else 'demo'
        elif sys.argv[1] in ['real', 'demo']:
            mode = sys.argv[1]
    
    print("=" * 60)
    print("🚀 BIAS-ATR 智能网格交易系统")
    print("=" * 60)
    print(f"📌 运行模式: {'🟢 真实数据' if mode == 'real' else '🟡 演示模式'}")
    print(f"📊 ETF池: {len(config.ETF_LIST)} 只")
    print(f"💰 总资金: ¥{config.TOTAL_CAPITAL:,.0f}")
    print("=" * 60)
    
    try:
        app = GridTraderGUI(mode=mode)
        app.run()
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()