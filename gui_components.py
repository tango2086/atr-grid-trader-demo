import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class StockChart(ttk.Frame):
    """股票K线图表组件"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.figure, self.ax = plt.subplots(figsize=(8, 6), dpi=100)
        self.figure.patch.set_facecolor('#1E1E1E') # 与卡片背景一致
        self.ax.set_facecolor('#121212') # 深色绘图区
        
        # 调整边距
        plt.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.15)
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 初始化空图表
        self.clear_chart()
        
    def clear_chart(self):
        """清空图表"""
        self.ax.clear()
        self.ax.set_facecolor('#121212')
        self.ax.tick_params(colors='white')
        self.ax.spines['bottom'].set_color('#333333')
        self.ax.spines['top'].set_color('#333333') 
        self.ax.spines['left'].set_color('#333333')
        self.ax.spines['right'].set_color('#333333')
        self.ax.text(0.5, 0.5, "请选择左侧ETF查看详情", 
                    transform=self.ax.transAxes, color='#666666', 
                    ha='center', va='center', fontsize=12)
        self.canvas.draw()

    def plot_data(self, df, orders=None, current_price=None, holdings=None, grid_pairs=None):
        """绘制K线数据 - [增强版] 添加网格可视化"""
        self.ax.clear()
        self.ax.set_facecolor('#121212')
        self.ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
        self.ax.tick_params(axis='x', colors='#A0A0A0')
        self.ax.tick_params(axis='y', colors='#A0A0A0')
        
        for spine in self.ax.spines.values():
            spine.set_color('#333333')

        if df is None or df.empty:
            self.ax.text(0.5, 0.5, "暂无数据", 
                        transform=self.ax.transAxes, color='#666666', 
                        ha='center', va='center', fontsize=12)
            self.canvas.draw()
            return

        # 准备数据 (取最近N条)
        limit = 60
        data = df.tail(limit).copy()
        
        # 绘制K线 (简单版：红涨绿跌)
        width = 0.6
        width2 = 0.1
        
        up = data[data.close >= data.open]
        down = data[data.close < data.open]
        
        col_up = '#ef4444' # 红
        col_down = '#10b981' # 绿
        
        # 绘制阳线
        self.ax.bar(up.index, up.close - up.open, width, bottom=up.open, color=col_up)
        self.ax.bar(up.index, up.high - up.close, width2, bottom=up.close, color=col_up)
        self.ax.bar(up.index, up.low - up.open, width2, bottom=up.open, color=col_up)
        
        # 绘制阴线
        self.ax.bar(down.index, down.close - down.open, width, bottom=down.open, color=col_down)
        self.ax.bar(down.index, down.high - down.open, width2, bottom=down.open, color=col_down)
        self.ax.bar(down.index, down.low - down.close, width2, bottom=down.close, color=col_down)

        # 绘制均线
        if 'ma_20' in data.columns:
            self.ax.plot(data.index, data['ma_20'], color='#f59e0b', linewidth=1, label='MA20', alpha=0.7)

        # [NEW] 绘制持仓成本线（紫色实线）
        if holdings and holdings.get('avg_cost', 0) > 0 and holdings.get('volume', 0) > 0:
            cost = holdings['avg_cost']
            self.ax.axhline(y=cost, color='#a855f7', linestyle='-', linewidth=1.5, alpha=0.8)
            self.ax.text(data.index[-1], cost, f' 成本 {cost:.3f}', 
                        color='#a855f7', va='center', fontsize=8, fontweight='bold')

        # [NEW] 绘制网格配对目标卖出价（橙色点线）
        if grid_pairs:
            for pair in grid_pairs:
                target_price = pair.get('target_sell_price', 0)
                if target_price > 0:
                    self.ax.axhline(y=target_price, color='#f97316', linestyle=':', linewidth=1, alpha=0.7)
                    self.ax.text(data.index[-1], target_price, f' 目标 {target_price:.3f}', 
                                color='#f97316', va='center', fontsize=7)

        # 绘制建议订单（买入绿色虚线，卖出红色虚线）
        if orders:
            for order in orders:
                # order结构可能不同，需兼容
                price = order.price if hasattr(order, 'price') else order.get('price')
                direction = order.direction if hasattr(order, 'direction') else order.get('direction')
                
                if direction == 'BUY':
                    color = '#10b981'  # 买入绿色
                    label = '买入'
                else:
                    color = '#ef4444'  # 卖出红色
                    label = '卖出'
                
                self.ax.axhline(y=price, color=color, linestyle='--', alpha=0.6)
                
                # 标注价格
                self.ax.text(data.index[-1], price, f' {label} {price:.3f}', 
                            color=color, va='center', fontsize=8)

        # 格式化X轴日期
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(self.ax.get_xticklabels(), rotation=30, ha='right')

        self.canvas.draw()

class GridVizPanel(ttk.Frame):
    """网格交易可视化面板 (底部详情)"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style='Card.TFrame', padding=10)
        
        # 1. 顶部：网格区间条
        self.create_interval_bar()
        
        # 2. 底部：订单详情块
        self.create_order_blocks()
        
    def create_interval_bar(self):
        """创建网格区间可视化条"""
        self.interval_frame = ttk.Frame(self)
        self.interval_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.interval_frame, text="网格区间位置", style='CardTitle.TLabel').pack(anchor=tk.W)
        
        self.canvas = tk.Canvas(self.interval_frame, height=40, bg='#1E1E1E', highlightthickness=0)
        self.canvas.pack(fill=tk.X, pady=5)
        
    def create_order_blocks(self):
        """创建订单详情块区域"""
        self.blocks_frame = ttk.Frame(self)
        self.blocks_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(self.blocks_frame, text="建议挂单详情", style='CardTitle.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        self.orders_container = ttk.Frame(self.blocks_frame, style='Card.TFrame')
        self.orders_container.pack(fill=tk.X)
        
    def update_data(self, current_price, orders, grid_info=None):
        """更新数据"""
        self.draw_interval_bar(current_price, grid_info)
        self.draw_order_blocks(orders)
        
    def draw_interval_bar(self, current_price, grid_info=None):
        """绘制区间条"""
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = 40
        if w < 10: w = 400 # 默认宽度
        
        # 模拟网格范围 (如果没传grid_info，就用当前价格上下10%模拟)
        if grid_info:
            lower = grid_info.get('lower', current_price * 0.9)
            upper = grid_info.get('upper', current_price * 1.1)
        else:
            lower = current_price * 0.95
            upper = current_price * 1.05
            
        # 绘制主轴线
        margin = 30
        line_y = h / 2
        start_x = margin
        end_x = w - margin
        
        self.canvas.create_line(start_x, line_y, end_x, line_y, fill='#666666', width=2)
        
        # 绘制端点
        self.canvas.create_line(start_x, line_y-5, start_x, line_y+5, fill='#666666', width=2)
        self.canvas.create_text(start_x, line_y+15, text=f"{lower:.3f}", fill='#A0A0A0', font=('Arial', 8))
        
        self.canvas.create_line(end_x, line_y-5, end_x, line_y+5, fill='#666666', width=2)
        self.canvas.create_text(end_x, line_y+15, text=f"{upper:.3f}", fill='#A0A0A0', font=('Arial', 8))
        
        # 绘制当前价格点
        # 映射价格到X坐标
        if upper > lower:
            ratio = (current_price - lower) / (upper - lower)
            ratio = max(0, min(1, ratio)) # 限制在0-1
            pos_x = start_x + ratio * (end_x - start_x)
            
            # 颜色根据位置变化 (低位绿，高位红)
            color = '#10b981' if ratio < 0.5 else '#ef4444'
            
            self.canvas.create_oval(pos_x-6, line_y-6, pos_x+6, line_y+6, fill=color, outline='white')
            self.canvas.create_text(pos_x, line_y-15, text=f"现价: {current_price:.3f}", fill='white', font=('Arial', 9, 'bold'))
            
    def draw_order_blocks(self, orders):
        """绘制可视化订单块"""
        # 清空
        for widget in self.orders_container.winfo_children():
            widget.destroy()
            
        if not orders:
            ttk.Label(self.orders_container, text="暂无建议订单", style='Status.TLabel').pack(anchor=tk.W, pady=10)
            return

        # 横向排列
        for order in orders:
            # order可能是对象或字典
            price = order.price if hasattr(order, 'price') else order.get('price')
            amount = order.amount if hasattr(order, 'amount') else order.get('amount')
            direction = order.direction if hasattr(order, 'direction') else order.get('direction')
            
            bg_color = '#ef4444' if direction == 'SELL' else '#3b82f6' # 卖红买蓝
            type_text = "卖出" if direction == 'SELL' else "买入"
            
            # 使用Canvas画自定义块，或者通过Frame模拟
            frame = tk.Frame(self.orders_container, bg='#2C2C2C', padx=10, pady=5)
            frame.pack(side=tk.LEFT, padx=(0, 10))
            
            # 左侧色条
            tk.Frame(frame, bg=bg_color, width=4, height=30).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
            
            # 内容
            info_frame = tk.Frame(frame, bg='#2C2C2C')
            info_frame.pack(side=tk.LEFT)
            
            tk.Label(info_frame, text=f"{type_text} {price:.3f}", fg='white', bg='#2C2C2C', font=('Microsoft YaHei', 10, 'bold')).pack(anchor=tk.W)
            tk.Label(info_frame, text=f"数量: {amount} 股", fg='#AAAAAA', bg='#2C2C2C', font=('Microsoft YaHei', 8)).pack(anchor=tk.W)

class StatusDashboard(ttk.Frame):
    """系统状态仪表盘 (右侧)"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style='Card.TFrame', padding=10)
        
        ttk.Label(self, text="系统状态", style='CardTitle.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        # 1. 核心状态指示
        self.status_canvas = tk.Canvas(self, height=80, bg='#1E1E1E', highlightthickness=0)
        self.status_canvas.pack(fill=tk.X)
        
        # 2. 统计数据
        self.stats_frame = tk.Frame(self, bg='#1E1E1E')
        self.stats_frame.pack(fill=tk.X, pady=10)
        
        self.create_stat_row("今日触发", "0 次")
        self.create_stat_row("监控标的", "0 只")
        
        self.draw_status(True, "运行中") # 默认状态
        
    def create_stat_row(self, label, value):
        row = tk.Frame(self.stats_frame, bg='#1E1E1E')
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label, fg='#A0A0A0', bg='#1E1E1E', width=10, anchor='w').pack(side=tk.LEFT)
        v_label = tk.Label(row, text=value, fg='white', bg='#1E1E1E', font=('Consolas', 10, 'bold'))
        v_label.pack(side=tk.RIGHT)
        return v_label
        
    def update_stats(self, trigger_count, monitor_count):
        # 简单更新方法，实际需保存引用
        # 这里为了演示，直接重建或查找子组件
        children = self.stats_frame.winfo_children()
        if len(children) >= 2:
            children[0].winfo_children()[1].config(text=f"{trigger_count} 次")
            children[1].winfo_children()[1].config(text=f"{monitor_count} 只")
            
    def draw_status(self, is_connected, status_text):
        """绘制状态灯"""
        self.status_canvas.delete("all")
        
        # 绿色/红色 呼吸灯效果
        color = '#10b981' if is_connected else '#ef4444'
        glow_color = '#059669' if is_connected else '#991b1b'
        
        # 光晕
        cx, cy = 40, 40
        r = 15
        for i in range(3):
            alpha = (3-i) * 0.2
            # 模拟光晕 (Canvas不支持alpha fill, 用stipple模拟或忽略)
            self.status_canvas.create_oval(cx-(r+i*4), cy-(r+i*4), cx+(r+i*4), cy+(r+i*4), 
                                         outline=glow_color, width=1)
            
        # 实体灯
        self.status_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=color, outline='white')
        
        # 文本
        self.status_canvas.create_text(90, cy, text=status_text, anchor='w', 
                                     fill=color, font=('Microsoft YaHei', 14, 'bold'))
        self.status_canvas.create_text(90, cy+20, text=datetime.now().strftime('%H:%M:%S'), anchor='w', 
                                     fill='#666666', font=('Consolas', 9))
