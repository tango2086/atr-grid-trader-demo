# web_server.py - Web 监控面板服务
"""
基于 Flask 的 Web 监控面板：
- 实时显示持仓和网格状态
- API 接口提供数据
- 自动刷新页面
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime
import threading
import time
import sqlite3
import config
from data_manager import get_data_manager
from strategy import GridStrategy
from indicators import calculate_indicators
from trader import get_trader, HAS_TRADER
from holdings_storage import init_holdings_from_local, update_holding_after_trade
from price_alert import alert_manager, PriceAlert
from persistence import grid_state_manager

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.jinja_env.auto_reload = True
app.config['EXPLAIN_TEMPLATE_LOADING'] = False

# 自定义 JSON 编码器处理 NaN 和 Infinity
import json
import math

def sanitize_for_json(obj):
    """递归清洗数据，将 NaN 和 Infinity 替换为 None"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    return obj

def safe_jsonify(data):
    """安全的 jsonify 替代函数，处理 NaN 值"""
    from flask import Response
    cleaned_data = sanitize_for_json(data)
    return Response(
        json.dumps(cleaned_data, ensure_ascii=False),
        mimetype='application/json'
    )

# 添加错误处理
@app.errorhandler(500)
def internal_error(error):
    import traceback
    return traceback.format_exc(), 500

# 全局状态
class MonitorState:
    def __init__(self):
        self.last_update = None
        self.etf_data = {}
        self.plans = {}
        self.data_manager = get_data_manager()
        self.strategy = GridStrategy()
        self.new_alerts = []  # 最新价格提醒
    
    def update(self):
        """更新所有 ETF 数据"""
        self.new_alerts = []  # 清空新提醒

        for code in config.ETF_LIST:
            try:
                # 获取历史数据
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

                # 保存数据
                last = df.iloc[-1]
                current_price = float(last['close'])

                # 准备订单数据用于价格提醒检测
                orders_data = [
                    {
                        'direction': o.direction,
                        'price': o.price,
                        'amount': o.amount,
                        'desc': o.desc
                    } for o in plan.suggested_orders
                ]

                # 检测价格提醒
                new_alerts = alert_manager.check_price_alerts(
                    code=code,
                    name=config.ETF_NAMES.get(code, code),
                    current_price=current_price,
                    suggested_orders=orders_data
                )

                # 添加到新提醒列表
                self.new_alerts.extend(new_alerts)

                self.etf_data[code] = {
                    'code': code,
                    'name': config.ETF_NAMES.get(code, code),
                    'price': current_price,
                    'atr': float(last['atr_14']), # [NEW] 存储ATR
                    'bias': float(plan.current_bias),
                    'status': plan.market_status,
                    'target_pos': plan.target_pos_pct,
                    'holdings': holdings,
                    'orders': orders_data,
                    'warnings': plan.warnings,
                    'support': plan.support,
                    'resistance': plan.resistance,
                    'new_alerts': [alert.to_dict() for alert in new_alerts]  # 该ETF的新提醒
                }
                self.plans[code] = plan

            except Exception as e:
                print(f"更新 {code} 失败: {e}")

        self.last_update = datetime.now()

state = MonitorState()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """获取状态 API"""
    # 计算汇总
    holdings_value = 0  # 持仓市值
    total_floating_pnl = 0  # 持仓浮盈
    
    for code, data in state.etf_data.items():
        holdings = data['holdings']
        price = data['price']
        vol = holdings.get('volume', 0)
        cost = holdings.get('avg_cost', 0)

        market_value = price * vol
        holdings_value += market_value
        if cost > 0 and vol > 0:
            total_floating_pnl += (price - cost) * vol

    # [NEW] 获取已实现盈亏
    from datetime import datetime
    today_str = datetime.now().strftime('%Y-%m-%d')
    today_realized_pnl = grid_state_manager.get_realized_pnl(start_date=today_str)
    all_time_realized_pnl = grid_state_manager.get_realized_pnl()
    
    # 总盈亏 = 当前持仓浮盈 + 历史已实现盈亏
    final_total_profit = total_floating_pnl + all_time_realized_pnl
    
    # [FIX] 总资产 = 初始资金 + 总盈亏 (= 剩余现金 + 持仓市值)
    total_value = float(config.TOTAL_CAPITAL) + final_total_profit

    # 准备新提醒数据
    new_alerts_data = []
    for alert in state.new_alerts:
        new_alerts_data.append(alert.to_dict())

    # 获取最近提醒统计
    alert_stats = alert_manager.get_alert_count(hours=24)

    return safe_jsonify({
            'timestamp': state.last_update.strftime('%Y-%m-%d %H:%M:%S') if state.last_update else '',
            'data_source': state.data_manager.get_data_source(),
            'etf_list': list(state.etf_data.values()),
            'summary': {
                'total_capital': float(config.TOTAL_CAPITAL),
                'total_value': float(total_value),
                'total_profit': float(final_total_profit),
                'profit_pct': float((final_total_profit / config.TOTAL_CAPITAL * 100) if config.TOTAL_CAPITAL > 0 else 0),
                'position_pct': float((total_value / config.TOTAL_CAPITAL * 100) if config.TOTAL_CAPITAL > 0 else 0),
                'day_profit': float(today_realized_pnl), # [NEW] 今日已纳税(实现)收益
                'floating_pnl': float(total_floating_pnl), # [NEW] 当前持仓浮盈
                'realized_pnl': float(all_time_realized_pnl) # [NEW] 累计已实现
            },
            'alerts': {
                'new_count': len(new_alerts_data),
                'new_alerts': new_alerts_data,
                'today_stats': alert_stats
            }
        })


@app.route('/api/refresh')
def api_refresh():
    """手动刷新数据"""
    state.update()
    return safe_jsonify({'status': 'ok', 'timestamp': datetime.now().strftime('%H:%M:%S')})


@app.route('/api/trader/status')
def api_trader_status():
    """获取交易服务状态"""
    trader = get_trader()
    return safe_jsonify({
        'has_trader': HAS_TRADER,
        'connected': trader.is_connected(),
        'auto_trade_enabled': config.TRADE_CONFIG.AUTO_TRADE_ENABLED,
        'account_id': config.TRADE_CONFIG.ACCOUNT_ID if HAS_TRADER else None
    })


@app.route('/api/trade', methods=['POST'])
def api_trade():
    """执行交易"""
    data = request.get_json()
    if not data:
        return safe_jsonify({'success': False, 'message': '无效的请求数据'}), 400

    code = data.get('code', '')
    direction = data.get('direction', '')
    price = data.get('price', 0)
    volume = data.get('volume', 0)

    # 验证参数
    if not code or not direction or price <= 0 or volume <= 0:
        return safe_jsonify({'success': False, 'message': '参数不完整或无效'}), 400

    if direction not in ['BUY', 'SELL']:
        return safe_jsonify({'success': False, 'message': '无效的交易方向'}), 400

    # 检查交易模块
    if not HAS_TRADER:
        return safe_jsonify({'success': False, 'message': 'XtTrader 未安装，无法交易'})

    # 执行下单
    trader = get_trader()

    # 如果未连接，尝试连接
    if not trader.is_connected():
        if not trader.connect():
            return safe_jsonify({'success': False, 'message': '交易服务连接失败，请检查XMT客户端'})

    # 下单 (confirm=False 因为通过Web确认)
    result = trader.place_order(code, direction, price, volume, confirm=False)

    if result.success:
        # [NEW] 记录交易历史和已实现盈亏
        realized_pnl = 0.0
        if direction == 'SELL':
            # 获取当前持仓成本 (在更新holdings之前或之后 update_holding_after_trade会更新avg_cost的)
            # 简单起见，我们使用这次卖出的价格 - 之前记录的平均成本(如果有)
            # 注意: update_holding_after_trade 刚刚已经执行了，那里的逻辑是减少持仓，avg_cost不变。
            # 所以 config.REAL_HOLDINGS[code]['avg_cost'] 应该还是准的。
            if code in config.REAL_HOLDINGS:
                avg_cost = config.REAL_HOLDINGS[code]['avg_cost']
                if avg_cost > 0:
                    realized_pnl = (price - avg_cost) * volume
        
        grid_state_manager.add_trade_record(code, direction, price, volume, realized_pnl)

        # [NEW] 网格配对逻辑 (Grid Pairing)
        try:
            if direction == 'BUY':
                # 计算目标卖出价(策略: 价格 + 2*ATR)
                target_sell_price = price * 1.03 # 默认保底 3%
                
                # 尝试获取最新ATR (从state缓存)
                if code in state.etf_data and 'atr' in state.etf_data[code]:
                    atr = state.etf_data[code]['atr']
                    if atr > 0:
                        target_sell_price = price + 2.0 * atr

                grid_state_manager.add_grid_pair(code, price, volume, target_sell_price)
                
            elif direction == 'SELL':
                # 尝试匹配并关闭对应网格
                active_pairs = grid_state_manager.get_active_pairs(code)
                for pair in active_pairs:
                    # 只要卖出价格 >= 目标价 * 0.99，就视为该网格止盈
                    if price >= pair['target_sell_price'] * 0.99:
                        grid_state_manager.close_pair(pair['id'])
                        print(f"[PAIR] 关联配对止盈: ID {pair['id']}")
                        break # 简单起见，一次交易只核销一个最接近的配对
                        
        except Exception as e:
            print(f"[WARN] 网格配对更新异常: {e}")

    return safe_jsonify({
        'success': result.success,
        'message': result.message,
        'order_id': result.order_id,
        'code': result.code,
        'direction': result.direction,
        'price': result.price,
        'volume': result.volume
    })


@app.route('/api/alerts')
def api_alerts():
    """获取价格提醒记录"""
    # 获取查询参数
    hours = request.args.get('hours', 24, type=int)
    code = request.args.get('code', None)

    if code:
        # 获取指定ETF的提醒
        alerts = alert_manager.get_alerts_by_code(code, hours)
    else:
        # 获取所有提醒
        alerts = alert_manager.get_recent_alerts(hours)

    return safe_jsonify({
        'hours': hours,
        'code': code,
        'alerts': [alert.to_dict() for alert in alerts],
        'count': len(alerts)
    })


@app.route('/api/alerts/stats')
def api_alerts_stats():
    """获取提醒统计信息"""
    hours = request.args.get('hours', 24, type=int)
    stats = alert_manager.get_alert_count(hours)
    return safe_jsonify({
        'hours': hours,
        'stats': stats
    })


@app.route('/api/alerts/clear', methods=['POST'])
def api_alerts_clear():
    """清理旧的提醒记录"""
    data = request.get_json() or {}
    days = data.get('days', 7, type=int)

    try:
        cleared_count = alert_manager.clear_old_alerts(days)
        return safe_jsonify({
            'success': True,
            'message': f'已清理 {cleared_count} 条过期提醒记录',
            'cleared_count': cleared_count
        })
    except Exception as e:
        return safe_jsonify({
            'success': False,
            'message': f'清理失败: {str(e)}'
        }), 500


@app.route('/api/trading-signals')
def api_trading_signals():
    hours = request.args.get('hours', default=24, type=int)
    # 模拟信号获取逻辑
    # 实际上应该从数据库或者 alerts 列表获取
    # 这里演示用，返回 alert_manager 的历史
    
    # 简单的适配
    signals = []
    # 这里我们也可以从 Recent Alerts 获取
    # 为了演示，我们可以从数据库读取 trade_history 作为已成交信号
    # 或者从 MonitorState.new_alerts
    
    # 暂时返回 MonitorState 中的 new_alerts (实时) + 模拟历史
    now_ts = datetime.now()
    
    # 真正实现: 
    # 应该建立一个 SignalManager 单独存储所有发出的信号
    # 这里简单 mock 一下或者复用 alert_manager (alert_manager是内存的)
    
    # 还是用 alert_manager 的历史记录吧
    # AlertManager 目前没有历史记录功能，添加一个?
    # 或者直接读取 state.new_alerts (虽然只有当次刷新)
    
    # 更好的方式：读取 trade_history 并标记为 'EXECUTED'
    # 这里简化：返回空列表或模拟数据，配合前端测试
    
    return jsonify({
        'success': True,
        'signals': [] # 暂无持久化信号
    })

# [NEW] 系统日志 API
@app.route('/api/logs')
def api_logs():
    from logger import get_logger
    logger = get_logger()
    limit = request.args.get('limit', default=50, type=int)
    # 获取最近日志
    if hasattr(logger, 'get_recent_logs'):
        logs = logger.get_recent_logs(limit)
    else:
        logs = []
    
    return jsonify({
        'success': True,
        'logs': logs
    })

# 启动后台线程
def start_background_task():
    """获取交易信号记录"""
    try:
        hours = request.args.get('hours', 24, type=int)
        code = request.args.get('code', None)

        # 获取价格提醒记录
        alerts = alert_manager.get_recent_alerts(hours)

        # 转换为交易信号格式
        signals = []
        for alert in alerts:
            alert_code = getattr(alert, 'code', '')
            if code and alert_code != code:
                continue

            target_price = getattr(alert, 'target_price', 0) or 0
            current_price = getattr(alert, 'current_price', getattr(alert, 'price', 0)) or 0
            
            signal = {
                'id': getattr(alert, 'id', ''),
                'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(alert, 'timestamp') else '',
                'code': alert_code,
                'name': getattr(alert, 'name', ''),
                'type': getattr(alert, 'direction', ''),
                'direction': getattr(alert, 'direction', ''),
                'target_price': target_price,
                'current_price': current_price,
                'amount': getattr(alert, 'amount', 0) or 0,
                'message': getattr(alert, 'message', ''),
                'status': 'pending',
                'priority': 'high' if target_price and current_price and abs(current_price - target_price) < 0.01 else 'normal'
            }
            signals.append(signal)

        # 按时间倒序排列
        signals.sort(key=lambda x: x['timestamp'], reverse=True)

        return safe_jsonify({
            'success': True,
            'signals': signals,
            'count': len(signals),
            'hours': hours,
            'code_filter': code
        })
    except Exception as e:
        return safe_jsonify({
            'success': False,
            'message': f'获取交易信号失败: {str(e)}',
            'signals': []
        }), 500


@app.route('/api/dashboard')
def api_dashboard():
    """获取仪表盘数据 - 简化版本"""
    try:
        # 计算基础汇总数据
        holdings_value = 0  # 持仓市值
        total_floating_pnl = 0

        for code, data in state.etf_data.items():
            holdings = data['holdings']
            price = data['price']
            vol = holdings.get('volume', 0)
            cost = holdings.get('avg_cost', 0)

            market_value = price * vol
            holdings_value += market_value
            if cost > 0 and vol > 0:
                total_floating_pnl += (price - cost) * vol

        # 获取已实现盈亏
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_realized_pnl = grid_state_manager.get_realized_pnl(start_date=today_str)
        all_time_realized_pnl = grid_state_manager.get_realized_pnl()
        final_total_profit = total_floating_pnl + all_time_realized_pnl
        
        # [FIX] 总资产 = 初始资金 + 总盈亏
        total_value = float(config.TOTAL_CAPITAL) + final_total_profit

        # 获取交易信号
        alerts = alert_manager.get_recent_alerts(24)
        signals = []
        for alert in alerts:
            target_price = getattr(alert, 'target_price', 0) or 0
            current_price = getattr(alert, 'current_price', getattr(alert, 'price', 0)) or 0
            signals.append({
                'id': getattr(alert, 'id', ''),
                'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S') if hasattr(alert, 'timestamp') else '',
                'code': getattr(alert, 'code', ''),
                'name': getattr(alert, 'name', ''),
                'direction': getattr(alert, 'direction', ''),
                'target_price': target_price,
                'current_price': current_price,
                'amount': getattr(alert, 'amount', 0) or 0,
                'message': getattr(alert, 'message', ''),
                'priority': 'high' if target_price and current_price and abs(current_price - target_price) < 0.01 else 'normal'
            })

        signals.sort(key=lambda x: x['timestamp'], reverse=True)
        today_signals = [s for s in signals if s['timestamp'].startswith(today_str)]

        # 返回仪表盘数据
        return safe_jsonify({
            'overview': {
                'total_capital': float(config.TOTAL_CAPITAL),
                'total_value': float(total_value),
                'total_profit': float(final_total_profit),
                'profit_pct': float((final_total_profit / config.TOTAL_CAPITAL * 100) if config.TOTAL_CAPITAL > 0 else 0),
                'position_pct': float((total_value / config.TOTAL_CAPITAL * 100) if config.TOTAL_CAPITAL > 0 else 0),
                'day_profit': float(today_realized_pnl),
                'floating_pnl': float(total_floating_pnl),
                'realized_pnl': float(all_time_realized_pnl)
            },
            'market_status': {
                'data_source': state.data_manager.get_data_source(),
                'last_update': state.last_update.strftime('%Y-%m-%d %H:%M:%S') if state.last_update else '',
                'etf_count': len(state.etf_data)
            },
            'signals': {
                'total': len(signals),
                'today': len(today_signals),
                'recent': signals[:5]
            },
            'trades': {
                'recent_count': 0,  # 暂时设为0，避免数据库访问错误
                'recent': []
            }
        })
    except Exception as e:
        return safe_jsonify({
            'success': False,
            'message': f'获取仪表盘数据失败: {str(e)}'
        }), 500


@app.route('/api/kline/<code>')
def api_kline(code):
    """获取ETF K线数据用于图表"""
    try:
        count = request.args.get('count', 60, type=int)
        df = state.data_manager.get_history(code, count=count)
        
        if df is None or df.empty:
            return safe_jsonify({'success': False, 'message': '无数据', 'data': []})
        
        # 计算指标
        df = calculate_indicators(df)
        
        # 转换为ECharts格式
        kline_data = []
        for idx, row in df.iterrows():
            # 使用简单的方法检查NaN：如果值是数字就转换，否则设为None
            ma5_val = row.get('ma_5')
            ma20_val = row.get('ma_20')
            bias_val = row.get('bias_20')

            # 尝试转换为float，失败则设为None
            try:
                ma5 = float(ma5_val)
            except (ValueError, TypeError):
                ma5 = None

            try:
                ma20 = float(ma20_val)
            except (ValueError, TypeError):
                ma20 = None

            try:
                bias = float(bias_val)
            except (ValueError, TypeError):
                bias = None

            kline_data.append({
                'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                'open': float(row['open']),
                'close': float(row['close']),
                'high': float(row['high']),
                'low': float(row['low']),
                'volume': float(row.get('volume', 0)),
                'ma5': ma5,
                'ma20': ma20,
                'bias': bias
            })
        
        # [NEW] 获取网格信息 (建议订单 + 持仓配对)
        grid_info = {'orders': [], 'active_pairs': []}
        if code in state.etf_data:
            grid_info['orders'] = state.etf_data[code].get('orders', [])
            grid_info['active_pairs'] = grid_state_manager.get_active_pairs(code)

        return safe_jsonify({
            'success': True,
            'code': code,
            'name': config.ETF_NAMES.get(code, code),
            'data': kline_data,
            'grid': grid_info
        })
    except Exception as e:
        return safe_jsonify({'success': False, 'message': str(e), 'data': []})


@app.route('/api/trades')
def api_trades():
    """获取历史交易记录（从提醒记录中提取）"""
    try:
        hours = request.args.get('hours', 168, type=int)  # 默认7天
        limit = request.args.get('limit', 50, type=int)
        
        # 从提醒记录获取交易相关信息
        alerts = alert_manager.get_recent_alerts(hours)
        
        trades = []
        for alert in alerts[:limit]:
            trades.append({
                'time': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'code': alert.code,
                'name': alert.name,
                'direction': alert.direction,
                'price': alert.target_price,
                'current_price': alert.current_price,
                'message': alert.message
            })
        
        return safe_jsonify({
            'success': True,
            'count': len(trades),
            'trades': trades
        })
    except Exception as e:
        return safe_jsonify({'success': False, 'message': str(e), 'trades': []})


@app.route('/api/trade_history')
def api_trade_history():
    """鑾峰彇鐪熷疄鐨勪氦鏄撳巻鍙茶褰曪紙浠庢暟鎹簱涓彁鍙栵級"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        # 浠庢暟鎹簱鑾峰彇鐪熷疄鐨勪氦鏄撳巻鍙茶褰?
        conn = sqlite3.connect('grid_state.db')
        # 杩斿洖瀛楀吀鍒楄〃
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trade_history ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trades.append({
                'id': row['id'],
                'code': row['code'],
                'direction': row['direction'],
                'price': row['price'],
                'volume': row['volume'],
                'realized_pnl': row['realized_pnl'],
                'timestamp': row['timestamp']
            })
        
        return safe_jsonify({
            'success': True,
            'count': len(trades),
            'trades': trades
        })
    except Exception as e:
        return safe_jsonify({'success': False, 'message': str(e), 'trades': []})


@app.route('/api/grid/<code>')
def api_grid(code):
    """Get ETF grid data"""
    try:
        if code not in state.etf_data:
            return safe_jsonify({'success': False, 'message': 'ETF not found'})
        
        data = state.etf_data[code]
        plan = state.plans.get(code)
        
        # Build grid visualization data
        grid_data = {
            'code': code,
            'name': data['name'],
            'current_price': data['price'],
            'support': data.get('support', []),
            'resistance': data.get('resistance', []),
            'orders': data['orders'],
            'bias': data['bias'],
            'status': data['status']
        }
        
        return safe_jsonify({'success': True, 'grid': grid_data})
    except Exception as e:
        return safe_jsonify({'success': False, 'message': str(e)})


def background_update():
    """Background update thread"""
    while True:
        try:
            state.update()
            print(f"[{datetime.now():%H:%M:%S}] Data updated")
        except Exception as e:
            print(f"Background update failed: {e}")
        # Use configured refresh interval
        interval = getattr(config.MONITOR_CONFIG, 'REFRESH_INTERVAL', 10)
        time.sleep(interval)


def run_server(host='0.0.0.0', port=5000, debug=False):
    """Start Web server"""
    print(f"\n[WEB] Web monitor starting...")
    print(f"   Address: http://localhost:{port}")
    print(f"   LAN access: http://<local-IP>:{port}")
    print(f"   Data source: {state.data_manager.get_data_source()}")
    
    # Load holdings from local file
    init_holdings_from_local()
    
    # First update
    state.update()
    
    # Start background update thread
    update_thread = threading.Thread(target=background_update, daemon=True)
    update_thread.start()
    
    # Start Flask
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    run_server()
