# strategy.py
import pandas as pd
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import config
from indicators import calculate_indicators
from persistence import grid_state_manager

@dataclass
class TradeOrder:
    direction: str  # 'BUY' or 'SELL'
    price: float
    amount: int     # 股数
    type: str = 'LIMIT'  # 'LIMIT' or 'MARKET'
    desc: str = ''

@dataclass
class TradePlan:
    code: str
    current_price: float
    current_bias: float
    market_status: str  # 状态: 深坑/黄金/震荡/减持/逃亡
    target_pos_pct: float
    suggested_orders: List[TradeOrder] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    risk_triggered: bool = False
    support: float = 0.0       # 支撑位
    resistance: float = 0.0    # 阻力位

class GridStrategy:
    def __init__(self):
        self.conf = config

    def _round_to_lot(self, amount: float) -> int:
        """向下取整到最近的 100 股"""
        return int(amount // self.conf.LOT_SIZE * self.conf.LOT_SIZE)
    
    def _detect_trend(self, df: pd.DataFrame) -> tuple:
        """
        检测趋势状态
        Returns: (is_uptrend, is_downtrend, description)
        """
        lookback = getattr(self.conf, 'TREND_TRACKING', None)
        if not lookback:
            return False, False, ""
        
        days = lookback.LOOKBACK_DAYS
        threshold = lookback.TREND_THRESHOLD
        
        if len(df) < days + 1:
            return False, False, ""
        
        # 获取最近N天的BIAS变化
        recent_bias = df['bias_20'].iloc[-(days+1):].values
        daily_changes = [recent_bias[i+1] - recent_bias[i] for i in range(days)]
        
        # 判断趋势
        all_rising = all(change > threshold for change in daily_changes)
        all_falling = all(change < -threshold for change in daily_changes)
        
        if all_rising:
            return True, False, f"连续{days}天上涨趋势 (每日+{threshold}%)"
        elif all_falling:
            return False, True, f"连续{days}天下跌趋势 (每日-{threshold}%)"
        
        return False, False, ""
    
    def _calc_dynamic_step(self, atr: float, price: float, zone: str) -> float:
        """
        计算动态网格间距
        基于ATR和波动率调整
        """
        # 基础间距系数
        grid_coef = self.conf.GRID_COEFFICIENT.get(zone, 1.0)
        base_step = atr * grid_coef
        
        # 动态调整
        dg = getattr(self.conf, 'DYNAMIC_GRID', None)
        if dg:
            atr_pct = atr / price  # ATR占价格百分比
            if atr_pct < dg.LOW_VOLATILITY_ATR:
                # 低波动: 缩小间距
                base_step *= dg.LOW_VOL_MULTIPLIER
            elif atr_pct > dg.HIGH_VOLATILITY_ATR:
                # 高波动: 扩大间距
                base_step *= dg.HIGH_VOL_MULTIPLIER
        
        # 最小利润保护 (动态调整)
        min_profit_pct = getattr(self.conf, 'MIN_PROFIT_PCT', 0.012)
        
        # [NEW] 动态止盈: 高波动时提高止盈目标
        dp_conf = getattr(self.conf, 'DYNAMIC_PROFIT_CONFIG', None)
        if dp_conf:
             atr_pct = atr / price
             if atr_pct > dp_conf.HIGH_VOLATILITY_PCT:
                 min_profit_pct = dp_conf.HIGH_PROFIT_TARGET
             elif atr_pct < dp_conf.LOW_VOLATILITY_PCT:
                 min_profit_pct = dp_conf.LOW_PROFIT_TARGET
                 
        min_step = price * min_profit_pct
        return max(base_step, min_step)
    
    def _calc_support_resistance(self, df: pd.DataFrame, lookback: int = 20) -> tuple:
        """
        计算支撑位和阻力位
        使用近N日最高/最低价
        
        Returns:
            (support, resistance, mid_price)
        """
        if len(df) < lookback:
            lookback = len(df)
        
        recent = df.iloc[-lookback:]
        support = recent['low'].min()
        resistance = recent['high'].max()
        mid_price = (support + resistance) / 2
        
        return support, resistance, mid_price
    
    def _adjust_grid_for_sr(self, price: float, support: float, resistance: float, 
                            step: float, direction: str) -> tuple:
        """
        根据支撑/阻力位调整网格
        
        Args:
            price: 当前价格
            support: 支撑位
            resistance: 阻力位
            step: 基础网格间距
            direction: 'BUY' 或 'SELL'
        
        Returns:
            (adjusted_price, weight_multiplier)
        """
        near_threshold = 0.02  # 接近阈值 2%
        
        if direction == 'BUY':
            # 买入：如果接近支撑位，加大权重
            distance_to_support = (price - support) / price
            if distance_to_support < near_threshold:
                # 非常接近支撑位，加大买入权重
                return max(support, price - step * 0.8), 1.5
            elif distance_to_support < near_threshold * 2:
                return price - step * 0.9, 1.2
        
        elif direction == 'SELL':
            # 卖出：如果接近阻力位，加大权重
            distance_to_resistance = (resistance - price) / price
            if distance_to_resistance < near_threshold:
                # 非常接近阻力位，加大卖出权重
                return min(resistance, price + step * 0.8), 1.5
            elif distance_to_resistance < near_threshold * 2:
                return price + step * 0.9, 1.2
        
        return None, 1.0  # 不调整

    def analyze(self, code: str, df: pd.DataFrame, current_holdings: Dict) -> TradePlan:
        """
        核心分析函数
        """
        # 1. 准备数据
        if 'bias_20' not in df.columns:
            df = calculate_indicators(df)

        if len(df) < 5:
            plan = TradePlan(code=code, current_price=0, current_bias=0, market_status="INSUFFICIENT_DATA", target_pos_pct=0.0)
            plan.warnings.append("数据不足")
            return plan

        current_data = df.iloc[-1]
        prev_data = df.iloc[-2]
        
        if pd.isna(current_data['bias_20']) or pd.isna(current_data['atr_14']):
            plan = TradePlan(code=code, current_price=current_data['close'], current_bias=0, market_status="INSUFFICIENT_INDICATORS", target_pos_pct=0.0)
            return plan

        bias = current_data['bias_20']
        prev_bias = prev_data['bias_20']
        price = current_data['close']
        atr = current_data['atr_14']
        
        # [NEW] 获取新指标
        rsi = current_data.get('rsi_14', 50)
        kdj_j = current_data.get('kdj_j', 50)
        
        # 3. 状态判定 (提前到锚定之前，因为锚定依赖状态)
        # 3.1 模式切换: BIAS 从上方跌破 3 (+3)
        bias_cross_down_3 = (prev_bias > self.conf.BIAS_THRESHOLDS.TREND_REVERSAL) and \
                            (bias <= self.conf.BIAS_THRESHOLDS.TREND_REVERSAL)
        
        # 标准分区判断
        if bias < self.conf.BIAS_THRESHOLDS.DEEP_DIP:
            zone = 'DEEP_DIP'
            market_status = "DEEP_DIP (深坑)"
        elif bias < self.conf.BIAS_THRESHOLDS.GOLD_ZONE_UPPER:
            zone = 'GOLD_ZONE'
            market_status = "GOLD_ZONE (黄金)"
        elif bias < self.conf.BIAS_THRESHOLDS.OSCILLATION_UPPER:
            zone = 'OSCILLATION'
            market_status = "OSCILLATION (震荡)"
        elif bias < self.conf.BIAS_THRESHOLDS.REDUCE_ZONE_UPPER:
            zone = 'REDUCE_ZONE'
            market_status = "REDUCE_ZONE (减持)"
        else:
            zone = 'ESCAPE_ZONE'
            market_status = "ESCAPE_ZONE (逃亡)"

        if bias_cross_down_3 and zone != 'DEEP_DIP':
             market_status = "OSCILLATION (SWITCH)"
             zone = 'OSCILLATION'
        
        # 计算支撑/阻力位
        support, resistance, _ = self._calc_support_resistance(df)

        # 初始计划
        plan = TradePlan(
            code=code,
            current_price=price,
            current_bias=bias,
            market_status=market_status,
            target_pos_pct=getattr(self.conf.TARGET_POSITION, zone),
            support=support,
            resistance=resistance
        )
        
        # [NEW] RSI 安全锁: 超买区(>75)禁止买入
        rsi_conf = getattr(self.conf, 'RSI_CONFIG', None)
        if rsi_conf and rsi > rsi_conf.SELL_THRESHOLD:
             plan.warnings.append(f"RSI超买({rsi:.1f}>{rsi_conf.SELL_THRESHOLD}). 暂停买入.")
             # 这里不强制设为0，但会在生成订单时过滤 BUY 单
             # 或者直接将 target_pos_pct 降级? 暂时仅做警告和过滤
             
        # [NEW] KDJ 超卖低吸信号
        is_kdj_oversold = (kdj_j < 10)
        if is_kdj_oversold and zone == 'DEEP_DIP':
             plan.warnings.append(f"KDJ超卖(J={kdj_j:.1f}). 触底信号.")

        # -----------------------------------------------------------
        # [CRITICAL UPDATE] 动态锚定逻辑 (Dynamic Anchoring)
        # -----------------------------------------------------------
        # 原逻辑: 始终锚定 ma_5
        # 新逻辑: 在 DEEP_DIP 或急跌时，ma_5 滞后严重，应锚定当前价格或更低，防止接飞刀
        
        if zone == 'DEEP_DIP':
            # 深坑模式：锚定当前价，且即使反弹也不急于上移锚点
            anchor_price = price
            anchor_source = "当前价格 (深坑动态)"
        else:
            # 正常模式：锚定5日线，平滑波动
            if pd.isna(current_data['ma_5']):
                anchor_price = price
                anchor_source = "当前价格 (无MA5)"
            else:
                anchor_price = current_data['ma_5']
                anchor_source = "5日均线"

        # -----------------------------------------------------------
        # 2. 风控检查
        # -----------------------------------------------------------
        current_vol = current_holdings.get('volume', 0)
        current_avail = current_holdings.get('available', 0)
        avg_cost = current_holdings.get('avg_cost', 0)

        # 阴跌熔断
        if current_vol > 0 and avg_cost > 0:
            pnl_pct = (price - avg_cost) / avg_cost
            if pnl_pct < self.conf.MAX_DRAWDOWN_LIMIT:
                plan.warnings.append(f"触发阴跌熔断: 浮亏 {pnl_pct*100:.2f}% >Limit. 暂停买入.")
                plan.risk_triggered = True

        # 趋势追踪
        is_uptrend, is_downtrend, trend_desc = self._detect_trend(df)
        if is_uptrend: plan.warnings.append(f"{trend_desc}. 暂停买入.")
        if is_downtrend: plan.warnings.append(f"{trend_desc}. 暂停卖出.")
        
        # 逃顶检查 (略简化，保留核心逻辑)
        if bias > self.conf.BIAS_THRESHOLDS.ESCAPE_TOP_HIGH:
            plan.market_status = "ESCAPE_HIGH"
            plan.target_pos_pct = 0.0
            # 这里应触发强制卖出信号，下文统一处理

        # -----------------------------------------------------------
        # [NEW] ATR 移动止损 (ATR Trailing Stop)
        # -----------------------------------------------------------
        # 计算近期高点 (20日)
        recent_high = df['high'].rolling(window=20).max().iloc[-1]
        retracement = recent_high - price
        
        # 只有在非下跌趋势中才主要考虑这个，或者作为强制风控
        # 如果回撤大于 3 * ATR，且当前持有仓位，则触发止损
        if retracement > 3 * atr and current_vol > 0:
            plan.warnings.append(f"🔴 触发ATR移动止损: 回撤({retracement:.3f}) > 3*ATR({3*atr:.3f})")
            plan.risk_triggered = True
            
            # 强制减仓 50%
            sell_vol = max(100, int(current_vol * 0.5))
            sell_vol = self._round_to_lot(sell_vol)
            if sell_vol > 0 and current_avail > 0:
                sell_amount = min(sell_vol, current_avail)
                plan.suggested_orders.append(TradeOrder(
                    direction='SELL',
                    price=price,
                    amount=sell_amount,
                    type='MARKET',
                    desc='ATR移动止损'
                ))
                return plan # 止损优先

        # -----------------------------------------------------------
        # [NEW] 网格配对卖出 (Grid Pairing Exit)
        # -----------------------------------------------------------
        active_pairs = grid_state_manager.get_active_pairs(code)
        for pair in active_pairs:
            # 如果当前价格 >= 目标卖出价，建议卖出
            # 注意：这里我们使用 LIMIT 单，价格为目标价（或者当前价，为了更容易成交）
            if price >= pair['target_sell_price'] * 0.995: # 0.5% 容差或精确
                target_sell_price = pair['target_sell_price']
                pair_amount = pair['buy_amount']
                
                if current_avail >= pair_amount:
                    plan.suggested_orders.append(TradeOrder(
                        direction='SELL',
                        price=max(price, target_sell_price), # 挂更优价格
                        amount=pair_amount,
                        type='LIMIT',
                        desc=f"配对止盈(ID:{pair['id']})"
                    ))
                    current_avail -= pair_amount # 扣除可用，避免重复计算
                    plan.warnings.append(f"⭐ 触发配对止盈: ID{pair['id']} 目标{target_sell_price:.3f}")
        
        # -----------------------------------------------------------
        # [CRITICAL UPDATE] 再平衡逻辑 (Rebalance)
        # -----------------------------------------------------------
        # 计算当前仓位比例
        total_assets = self.conf.CAPITAL_PER_ETF # 假设单只ETF固定资金池
        current_value = price * current_vol
        current_pos_pct = current_value / total_assets if total_assets > 0 else 0
        
        target_pos_pct = plan.target_pos_pct
        pos_deviation = target_pos_pct - current_pos_pct
        
        REBALANCE_THRESHOLD = 0.15 # 15% 偏差触发再平衡
        
        # 如果偏差巨大，且不在熔断/逃顶状态 -> 触发再平衡市价单
        if pos_deviation > REBALANCE_THRESHOLD and not plan.risk_triggered and zone in ['DEEP_DIP', 'GOLD_ZONE']:
            # 需要大幅补仓
            # 补足一半偏差，避免一次性冲击
            need_pct = pos_deviation * 0.5
            buy_value = total_assets * need_pct
            buy_amount = self._round_to_lot(buy_value / price)
            
            if buy_amount > 0:
                plan.suggested_orders.append(TradeOrder(
                    direction='BUY',
                    price=price, # 市价单逻辑
                    amount=buy_amount,
                    type='MARKET',
                    desc=f'再平衡补仓: 偏差 {pos_deviation*100:.1f}% > 15%'
                ))
                plan.warnings.append("触发再平衡: 仓位严重不足，优先执行市价补仓")
                return plan # 优先执行再平衡，不生成网格单

        # -----------------------------------------------------------
        # 4. 网格计算
        # -----------------------------------------------------------
        step_price = self._calc_dynamic_step(atr, anchor_price, zone)
        lot_value = self.conf.CAPITAL_PER_ETF * 0.05
        lot_amount = max(self._round_to_lot(lot_value / anchor_price), self.conf.LOT_SIZE)
        
        if zone == 'DEEP_DIP':
            # 深坑区：买入为主，暂时忽略趋势检测以便测试
            if not plan.risk_triggered:
                # [NEW] KDJ 优化: 如果J值超卖，且在深坑，尝试挂更近的单子接飞刀(?), 或者保持原样?
                # 策略: 如果 J < 0 (极度超卖)，可能即将反转，保持激进买入
                # 如果 RSI > 75，则跳过买入 (防止买在反弹高点)
                
                if rsi > 75: 
                    pass # 跳过
                else:
                    # 挂买1, 买2
                    buy1_price = anchor_price - step_price
                    # [NEW] 均值回归加速: 如果 KDJ 金叉(J上穿0)，可以考虑市价买入? 暂时保持限价
                    
                    plan.suggested_orders.append(TradeOrder('BUY', buy1_price, int(lot_amount*1.5), 'LIMIT', '深坑网格买1'))
                    plan.suggested_orders.append(TradeOrder('BUY', anchor_price - 2*step_price, int(lot_amount*1.5), 'LIMIT', '深坑网格买2'))
        
        elif zone in ['REDUCE_ZONE', 'ESCAPE_ZONE', 'ESCAPE_HIGH']:
             if current_avail > 0 and not is_downtrend:
                 sell_price = anchor_price + step_price
                 # 确保卖出价高于成本 (可选，这里暂不强制，优先减仓)
                 plan.suggested_orders.append(TradeOrder('SELL', sell_price, min(current_avail, int(lot_amount*1.5)), 'LIMIT', '减持网格卖1'))
        
        else:
            # 震荡/黄金区
            if not plan.risk_triggered and not is_uptrend:
                if rsi < 75: # RSI 过滤
                     plan.suggested_orders.append(TradeOrder('BUY', anchor_price - step_price, lot_amount, 'LIMIT', '网格买1'))
            
            if current_avail > 0 and not is_downtrend:
                plan.suggested_orders.append(TradeOrder('SELL', anchor_price + step_price, min(current_avail, lot_amount), 'LIMIT', '网格卖1'))

        return plan