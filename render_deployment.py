# render_deployment.py
# 针对 Render 平台部署的修改版本

import os
from flask import Flask, render_template, jsonify
import sqlite3
import threading
import time
from datetime import datetime
import json
import math

# 创建 Flask 应用
app = Flask(__name__)

# Render 提供的 PORT 环境变量
port = int(os.environ.get('PORT', 5000))

# ===== 修改 1: 使用临时数据库或外部数据库 =====
# 使用文件系统数据库（Render 重启后会丢失，但演示足够）
DATABASE_URL = 'sqlite:///grid_state.db'

def init_db():
    """初始化数据库"""
    os.makedirs('instance', exist_ok=True)
    conn = sqlite3.connect('grid_state.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            direction TEXT,
            price REAL,
            volume INTEGER,
            realized_pnl REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grid_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            buy_price REAL,
            volume INTEGER,
            target_sell_price REAL,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            closed_at DATETIME
        )
    ''')
    conn.commit()
    conn.close()

# ===== 修改 2: 简化的数据获取（模拟数据） =====
def get_mock_data():
    """获取模拟的 ETF 数据（用于演示）"""
    mock_etfs = {
        "sh510050": {"name": "上证50", "price": 3.15, "change": 0.02},
        "sh588090": {"name": "科创50", "price": 1.08, "change": -0.01},
        "sz159841": {"name": "证券ETF", "price": 1.20, "change": 0.03},
        "sh512480": {"name": "半导体", "price": 1.45, "change": 0.01},
        "sh512760": {"name": "芯片ETF", "price": 1.78, "change": -0.02}
    }

    # 添加随机波动
    import random
    for code, data in mock_etfs.items():
        data['price'] *= (1 + random.uniform(-0.005, 0.005))
        data['atr'] = data['price'] * random.uniform(0.015, 0.03)
        data['bias'] = random.uniform(-5, 10)
        data['ma5'] = data['price'] * random.uniform(0.98, 1.02)
        data['ma20'] = data['price'] * random.uniform(0.95, 1.05)
        data['volume'] = random.randint(10000, 100000)

    return mock_etfs

# ===== 修改 3: 安全的 JSON 响应 =====
def safe_jsonify(data):
    """安全的 jsonify 替代函数，处理 NaN 值"""
    def sanitize_for_json(obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif isinstance(obj, dict):
            return {k: sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [sanitize_for_json(item) for item in obj]
        return obj

    cleaned_data = sanitize_for_json(data)
    return Response(
        json.dumps(cleaned_data, ensure_ascii=False),
        mimetype='application/json'
    )

# ===== 主要路由 =====
@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """获取状态 API"""
    # 使用模拟数据
    etf_data = get_mock_data()

    # 计算汇总（模拟）
    total_capital = 200000
    total_value = total_capital * 1.05  # 模拟 5% 盈利
    total_profit = total_value - total_capital

    return safe_jsonify({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data_source': 'mock_data',  # 标记为模拟数据
        'etf_list': [
            {
                'code': code,
                'name': data['name'],
                'price': round(data['price'], 3),
                'atr': round(data['atr'], 3),
                'bias': round(data['bias'], 2),
                'status': '震荡' if -3 < data['bias'] < 5 else '买入' if data['bias'] < -3 else '卖出',
                'target_pos': 0.5,
                'holdings': {'volume': 10000, 'available': 10000, 'avg_cost': data['price'] * 0.95},
                'orders': [
                    {
                        'direction': 'BUY',
                        'price': round(data['price'] * 0.97, 3),
                        'amount': 1000,
                        'desc': '网格买入'
                    }
                ],
                'warnings': [],
                'support': [round(data['price'] * 0.95, 3)],
                'resistance': [round(data['price'] * 1.05, 3)],
                'new_alerts': []
            }
            for code, data in etf_data.items()
        ],
        'summary': {
            'total_capital': total_capital,
            'total_value': total_value,
            'total_profit': total_profit,
            'profit_pct': 5.0,
            'position_pct': 95.0,
            'day_profit': 500,
            'floating_pnl': 10000,
            'realized_pnl': 5000
        },
        'alerts': {
            'new_count': 0,
            'new_alerts': [],
            'today_stats': {'buy': 2, 'sell': 1, 'total': 3}
        }
    })

@app.route('/api/refresh')
def api_refresh():
    """手动刷新数据"""
    return safe_jsonify({'status': 'ok', 'timestamp': datetime.now().strftime('%H:%M:%S')})

@app.route('/api/kline/<code>')
def api_kline(code):
    """获取K线数据（模拟）"""
    import random
    from datetime import datetime, timedelta

    # 生成60天的模拟K线数据
    kline_data = []
    base_price = 3.0

    for i in range(60):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        price = base_price * (1 + random.uniform(-0.03, 0.03))

        kline_data.append({
            'date': date,
            'open': round(price * 0.995, 3),
            'close': round(price, 3),
            'high': round(price * 1.01, 3),
            'low': round(price * 0.99, 3),
            'volume': random.randint(10000, 100000),
            'ma5': round(price * random.uniform(0.98, 1.02), 3),
            'ma20': round(price * random.uniform(0.95, 1.05), 3),
            'bias': round(random.uniform(-5, 10), 2)
        })

    return safe_jsonify({
        'success': True,
        'code': code,
        'name': '演示ETF',
        'data': list(reversed(kline_data)),  # 按时间正序
        'grid': {
            'orders': [],
            'active_pairs': []
        }
    })

# 其他必要的路由（简化版）
@app.route('/api/trader/status')
def api_trader_status():
    """交易服务状态（模拟）"""
    return safe_jsonify({
        'has_trader': False,  # Render 上不启用真实交易
        'connected': False,
        'auto_trade_enabled': False,
        'account_id': None
    })

@app.route('/api/trade', methods=['POST'])
def api_trade():
    """交易接口（禁用）"""
    return safe_jsonify({
        'success': False,
        'message': '演示版本，不支持实际交易'
    }), 403

@app.route('/api/alerts')
def api_alerts():
    """价格提醒（模拟）"""
    return safe_jsonify({
        'hours': 24,
        'alerts': [],
        'count': 0
    })

@app.route('/api/dashboard')
def api_dashboard():
    """仪表盘数据"""
    return api_status()  # 复用状态数据

@app.route('/api/trade_history')
def api_trade_history():
    """交易历史（空）"""
    return safe_jsonify({
        'success': True,
        'count': 0,
        'trades': []
    })

# 健康检查端点（Render 需要）
@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'healthy'})

# ===== 修改 4: 生产环境配置 =====
if __name__ == '__main__':
    # 初始化数据库
    init_db()

    # 生产模式
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )