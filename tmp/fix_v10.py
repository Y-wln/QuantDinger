# Comprehensive fix: per-coin params, ATR dynamic SL, fast-coin 15m trigger
with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    content = f.read()

# 1. Add atr to imports
content = content.replace(
    'from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands,',
    'from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands, atr,')
content = content.replace(
    '    fetch_klines, fetch_oi, fetch_funding_rate, ema, rsi, calc_cvd)',
    '    fetch_klines, fetch_oi, fetch_funding_rate, ema, rsi, calc_cvd, load_state as hc_load_state, save_state as hc_save_state)')

# 2. Add per-coin config after SL_PCT/TP_PCT
old_config = \"\"\"MAX_POS = 8       # 最多持仓
SL_PCT = 0.04     # 止损4%
TP_PCT = 0.06     # 止盈6%\"\"\"

new_config = \"\"\"MAX_POS = 8       # 最多持仓
SL_PCT = 0.04     # 止损4% (fallback)
TP_PCT = 0.06     # 止盈6% (fallback)

# Per-coin params: threshold, ATR_SL_mult, ATR_TP_mult
# Fast coins (high vol): lower threshold + wider SL
# Slow coins (BTC-like): higher threshold + tighter SL
COIN_PARAMS = {
    'INJUSDT':  {'threshold': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'CHZUSDT':  {'threshold': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'DASHUSDT': {'threshold': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'TAOUSDT':  {'threshold': 10, 'sl_atr': 2.5, 'tp_atr': 4.0, 'fast': True},
    'FETUSDT':  {'threshold': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'ENAUSDT':  {'threshold': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'ONDOUSDT': {'threshold': 10, 'sl_atr': 2.5, 'tp_atr': 4.0, 'fast': False},
    'TONUSDT':  {'threshold': 12, 'sl_atr': 2.0, 'tp_atr': 3.5, 'fast': False},
    'PEPEUSDT': {'threshold': 8,  'sl_atr': 3.5, 'tp_atr': 6.0, 'fast': True},
    'WIFUSDT':  {'threshold': 8,  'sl_atr': 3.0, 'tp_atr': 5.0, 'fast': True},
    'BONKUSDT': {'threshold': 8,  'sl_atr': 3.5, 'tp_atr': 6.0, 'fast': True},
}
DEFAULT_PARAMS = {'threshold': 10, 'sl_atr': 2.0, 'tp_atr': 3.5, 'fast': False}\"\"\"

content = content.replace(old_config, new_config)

# 3. Replace analyze_one with per-coin aware version
old_analyze_start = 'def analyze_one(sym):'
old_analyze_end = '        return None\n'
# Find analyze_one function boundaries
idx_start = content.index(old_analyze_start)
# Find the function return at the end
idx_func_end = content.index('def scan():', idx_start)

old_func = content[idx_start:idx_func_end]
new_func = '''def analyze_one(sym):
    """妖币分析 v10 - 逐币参数 + ATR动态止损 + 快币15m先行"""
    try:
        cp = COIN_PARAMS.get(sym, DEFAULT_PARAMS)
        threshold = cp['threshold']
        is_fast = cp['fast']

        # 1h K线
        k1 = fetch_klines(sym, '1h', 100)
        if len(k1) < 50: return None
        c = [k['c'] for k in k1]
        rs_arr = rsi(c)
        rs = float(rs_arr[-1]) if isinstance(rs_arr, list) and len(rs_arr) > 0 else 50
        cv = calc_cvd(k1, 6)
        e20_arr = ema(c, 20)
        e50_arr = ema(c, 50)
        e20 = float(e20_arr[-1]) if isinstance(e20_arr, list) and len(e20_arr) > 0 else c[-1]
        e50 = float(e50_arr[-1]) if isinstance(e50_arr, list) and len(e50_arr) > 0 else c[-1]
        price = c[-1]
        trend_1h = 'up' if price > e20 and e20 > e50 else ('down' if price < e20 and e20 < e50 else 'neutral')

        # 15m K线 (快币优先)
        trend_15m = 'neutral'
        cv_15m = 0
        k15 = fetch_klines(sym, '15m', 60)
        if k15 and len(k15) >= 30:
            cv_15m = calc_cvd(k15, 6)
            c15 = [k['c'] for k in k15]
            e15_20 = ema(c15, 20)
            e15_50 = ema(c15, 50)
            if isinstance(e15_20, list) and len(e15_20)>0 and isinstance(e15_50, list) and len(e15_50)>0:
                p15 = c15[-1]
                e20_15 = float(e15_20[-1])
                e50_15 = float(e15_50[-1])
                trend_15m = 'up' if p15 > e20_15 and e20_15 > e50_15 else ('down' if p15 < e20_15 and e20_15 < e50_15 else 'neutral')

        # CVD加速度
        cv_prev = calc_cvd(k1[-12:-6], 6) if len(k1) >= 12 else cv
        cv_delta = cv - cv_prev
        cv_accel = 'accelerating' if abs(cv_delta) > 5 else ('stable' if abs(cv_delta) > 2 else 'flat')

        # Bollinger squeeze
        bb = bollinger_bands(c, 20, 2)
        bb_bw = bb["bandwidth"] if bb else 50
        bb_squeeze = bb.get("squeeze", False) if bb else False

        # ATR for dynamic SL/TP
        atr_val = atr(k1, 14)

        score = 0
        reasons = []

        # === CVD ===
        # Fast coins: 15m CVD gets priority
        if is_fast:
            if cv_15m > 20: score += 12; reasons.append('15mCVD多头'+str(int(cv_15m))+'%')
            elif cv_15m < -20: score -= 12; reasons.append('15mCVD空头'+str(int(cv_15m))+'%')
            elif cv_15m > 10: score += 6; reasons.append('15mCVD偏多'+str(int(cv_15m))+'%')
            elif cv_15m < -10: score -= 6; reasons.append('15mCVD偏空'+str(int(cv_15m))+'%')
            # 1h CVD as secondary
            if cv > 20: score += 6; reasons.append('1hCVD多头'+str(int(cv))+'%')
            elif cv < -20: score -= 6; reasons.append('1hCVD空头'+str(int(cv))+'%')
        else:
            if cv > 20: score += 10; reasons.append('1hCVD多头'+str(int(cv))+'%')
            elif cv < -20: score -= 10; reasons.append('1hCVD空头'+str(int(cv))+'%')
            elif cv > 10: score += 5; reasons.append('1hCVD偏多'+str(int(cv))+'%')
            elif cv < -10: score -= 5; reasons.append('1hCVD偏空'+str(int(cv))+'%')
            # 15m CVD as secondary
            if cv_15m > 20: score += 6; reasons.append('15mCVD多头'+str(int(cv_15m))+'%')
            elif cv_15m < -20: score -= 6; reasons.append('15mCVD空头'+str(int(cv_15m))+'%')

        # === CVD加速度 ===
        if cv > 10 and cv_accel == 'accelerating': score += 10; reasons.append('CVD加速买入')
        elif cv < -10 and cv_accel == 'accelerating': score -= 10; reasons.append('CVD加速卖出')

        # === RSI ===
        if rs < 25: score += 10; reasons.append('RSI超卖'+str(int(rs)))
        elif rs < 35: score += 5; reasons.append('RSI超卖'+str(int(rs)))
        elif rs > 75: score -= 10; reasons.append('RSI超买'+str(int(rs)))
        elif rs > 65: score -= 5; reasons.append('RSI超买'+str(int(rs)))

        # === 布林 ===
        if bb_squeeze:
            if cv > 5: score += 8; reasons.append('布林收缩+偏多')
            elif cv < -5: score -= 8; reasons.append('布林收缩+偏空')

        # === 趋势共振 ===
        if trend_1h == 'up' and trend_15m == 'up': score += 12; reasons.append('双周期共振向上')
        elif trend_1h == 'down' and trend_15m == 'down': score -= 12; reasons.append('双周期共振向下')
        elif trend_1h == 'up': score += 6; reasons.append('1h趋势向上')
        elif trend_1h == 'down': score -= 6; reasons.append('1h趋势向下')
        elif trend_15m == 'up': score += 4; reasons.append('15m趋势向上')
        elif trend_15m == 'down': score -= 4; reasons.append('15m趋势向下')

        # === 5m 放量 ===
        try:
            k5 = fetch_klines(sym, '5m', 30)
            if k5 and len(k5) >= 10:
                v5 = [k['v'] for k in k5]
                avg5 = sum(v5[-9:-1]) / 8 if len(v5) >= 9 else 1
                if avg5 > 0:
                    vr = v5[-1] / avg5
                    if vr > 2.5: score += 10; reasons.append('5m爆量'+str(round(vr,1))+'x')
                    elif vr > 1.8: score += 6; reasons.append('5m放量'+str(round(vr,1))+'x')
                    elif vr > 1.3: score += 3; reasons.append('5m微放量'+str(round(vr,1))+'x')
        except Exception: pass

        sig = 'long' if score >= threshold else ('short' if score <= -threshold else 'wait')
        return {'sym': sym, 'signal': sig, 'score': score, 'price': price,
            'reasons': reasons, 'cvd': round(cv,1), 'rsi': round(rs,0), 'trend': trend_1h,
            'atr': round(atr_val, 4), 'params': cp}
    except Exception as e:
        return None

'''

content = content[:idx_start] + new_func + content[idx_func_end:]

# 4. Update position management to use ATR-based SL/TP
# Replace the SL/TP assignment in scan() function
content = content.replace(
    \"            positions[sym] = {'direction':'long','entry':s['price'],'sl':s['price']*(1-SL_PCT),\",
    \"            atr_sl = s.get('atr', 0.01) * s.get('params', DEFAULT_PARAMS)['sl_atr']\n            atr_tp = s.get('atr', 0.01) * s.get('params', DEFAULT_PARAMS)['tp_atr']\n            positions[sym] = {'direction':'long','entry':s['price'],'sl':s['price']*(1-SL_PCT),\"")
content = content.replace(
    \"            positions[sym] = {'direction':'short','entry':s['price'],'sl':s['price']*(1+SL_PCT),\",
    \"            atr_sl = s.get('atr', 0.01) * s.get('params', DEFAULT_PARAMS)['sl_atr']\n            atr_tp = s.get('atr', 0.01) * s.get('params', DEFAULT_PARAMS)['tp_atr']\n            positions[sym] = {'direction':'short','entry':s['price'],'sl':s['price']*(1+SL_PCT),\"")
# Actually ATR SL should be used instead of SL_PCT. Let me do simpler replace:
content = content.replace(
    'sl':s['price']*(1-SL_PCT),\n                'tp':s['price']*(1+TP_PCT),
    'sl':s['price']-s.get('atr',0.01)*s.get('params',DEFAULT_PARAMS)['sl_atr'],\n                'tp':s['price']+s.get('atr',0.01)*s.get('params',DEFAULT_PARAMS)['tp_atr'])
content = content.replace(
    'sl':s['price']*(1+SL_PCT),\n                'tp':s['price']*(1-TP_PCT),
    'sl':s['price']+s.get('atr',0.01)*s.get('params',DEFAULT_PARAMS)['sl_atr'],\n                'tp':s['price']-s.get('atr',0.01)*s.get('params',DEFAULT_PARAMS)['tp_atr'])

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.write(content)
import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('v10 upgrade applied')
