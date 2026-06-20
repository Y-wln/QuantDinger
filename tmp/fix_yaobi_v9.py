# Fix yaobi analyze_one: add 15m CVD, CVD acceleration, Bollinger squeeze, multi-timeframe
with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    content = f.read()

# 1. Add bollinger_bands to import
content = content.replace(
    'from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send,',
    'from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands,')

# 2. Add fetch_oi import (it's already there? let me check)
# Actually fetch_oi is already imported. Good.

# 3. Replace the analyze_one function
old_analyze = '''def analyze_one(sym):
    \"\"\"???? - 1h + CVD + RSI + 5m??\"\"\"
    try:
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
        trend = 'up' if price > e20 and e20 > e50 else ('down' if price < e20 and e20 < e50 else 'neutral')
        score = 0
        reasons = []

        # CVD (?????, ????)
        if cv > 20: score += 12; reasons.append('CVD多头'+str(int(cv))+'%')
        elif cv < -20: score -= 12; reasons.append('CVD空头'+str(int(cv))+'%')
        elif cv > 10: score += 6; reasons.append('CVD多头'+str(int(cv))+'%')
        elif cv < -10: score -= 6; reasons.append('CVD空头'+str(int(cv))+'%')
        # RSI (?????)
        if rs < 25: score += 12; reasons.append('RSI超卖'+str(int(rs)))
        elif rs < 35: score += 6; reasons.append('RSI超卖'+str(int(rs)))
        elif rs > 75: score -= 12; reasons.append('RSI超买'+str(int(rs)))
        elif rs > 65: score -= 6; reasons.append('RSI超买'+str(int(rs)))
        # ??
        if trend == 'up': score += 8; reasons.append('趋势向上')
        elif trend == 'down': score -= 8; reasons.append('趋势向下')
        # 5m??
        try:
            k5 = fetch_klines(sym, '5m', 30)
            if k5 and len(k5) >= 10:
                v5 = [k['v'] for k in k5]
                avg5 = sum(v5[-9:-1]) / 8 if len(v5) >= 9 else 1
                if avg5 > 0:
                    vr = v5[-1] / avg5
                    if vr > 2.0: score += 8; reasons.append('5m放量'+str(round(vr,1))+'x')
                    elif vr > 1.5: score += 4; reasons.append('5m微放量'+str(round(vr,1))+'x')
        except Exception: pass

        sig = 'long' if score >= 12 else ('short' if score <= -12 else 'wait')
        return {'sym': sym, 'signal': sig, 'score': score, 'price': price,
            'reasons': reasons, 'cvd': round(cv,1), 'rsi': round(rs,0), 'trend': trend}
    except Exception as e:
        return None'''

new_analyze = '''def analyze_one(sym):
    """妖币分析 v9 - 1h/15m双周期 + CVD加速度 + 布林收缩 + 多周期共振"""
    try:
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

        # 15m K-line for faster CVD + trend
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

        # CVD acceleration (rate of change)
        cv_prev = calc_cvd(k1[-12:-6], 6) if len(k1) >= 12 else cv
        cv_delta = cv - cv_prev
        cv_accel = 'accelerating' if abs(cv_delta) > 5 else ('stable' if abs(cv_delta) > 2 else 'flat')

        # Bollinger squeeze
        bb_upper, bb_mid, bb_lower, bb_bw = bollinger_bands(c, 20, 2)
        bb_squeeze = bb_bw < 8

        score = 0
        reasons = []

        # === 1h CVD (大周期方向) ===
        if cv > 20: score += 10; reasons.append('1hCVD多头'+str(int(cv))+'%')
        elif cv < -20: score -= 10; reasons.append('1hCVD空头'+str(int(cv))+'%')
        elif cv > 10: score += 5; reasons.append('1hCVD偏多'+str(int(cv))+'%')
        elif cv < -10: score -= 5; reasons.append('1hCVD偏空'+str(int(cv))+'%')

        # === 15m CVD (小周期先行) ===
        if cv_15m > 20: score += 8; reasons.append('15mCVD多头'+str(int(cv_15m))+'%')
        elif cv_15m < -20: score -= 8; reasons.append('15mCVD空头'+str(int(cv_15m))+'%')
        elif cv_15m > 10: score += 4; reasons.append('15mCVD偏多'+str(int(cv_15m))+'%')
        elif cv_15m < -10: score -= 4; reasons.append('15mCVD偏空'+str(int(cv_15m))+'%')

        # === CVD加速度 (资金加速流入/流出) ===
        if cv > 10 and cv_accel == 'accelerating': score += 10; reasons.append('CVD加速买入')
        elif cv < -10 and cv_accel == 'accelerating': score -= 10; reasons.append('CVD加速卖出')

        # === RSI ===
        if rs < 25: score += 10; reasons.append('RSI超卖'+str(int(rs)))
        elif rs < 35: score += 5; reasons.append('RSI超卖'+str(int(rs)))
        elif rs > 75: score -= 10; reasons.append('RSI超买'+str(int(rs)))
        elif rs > 65: score -= 5; reasons.append('RSI超买'+str(int(rs)))

        # === 布林带收缩 (暴风雨前夜) ===
        if bb_squeeze:
            if cv > 5: score += 8; reasons.append('布林收缩+资金偏多(蓄势突破)')
            elif cv < -5: score -= 8; reasons.append('布林收缩+资金偏空(蓄势下跌)')
            else: reasons.append('布林收缩(方向待定)')

        # === 多周期趋势共振 ===
        if trend_1h == 'up' and trend_15m == 'up': score += 12; reasons.append('双周期共振向上')
        elif trend_1h == 'down' and trend_15m == 'down': score -= 12; reasons.append('双周期共振向下')
        elif trend_1h == 'up': score += 6; reasons.append('1h趋势向上')
        elif trend_1h == 'down': score -= 6; reasons.append('1h趋势向下')
        elif trend_15m == 'up': score += 4; reasons.append('15m趋势向上')
        elif trend_15m == 'down': score -= 4; reasons.append('15m趋势向下')

        # === 5m 放量 (启动确认) ===
        try:
            k5 = fetch_klines(sym, '5m', 30)
            if k5 and len(k5) >= 10:
                v5 = [k['v'] for k in k5]
                avg5 = sum(v5[-9:-1]) / 8 if len(v5) >= 9 else 1
                if avg5 > 0:
                    vr = v5[-1] / avg5
                    if vr > 2.5: score += 10; reasons.append('5m爆量'+str(round(vr,1))+'x')
                    elif vr > 1.8: score += 6; reasons.append('5m放量'+str(round(vr,1))+'x')
                    elif vr > 1.3: score += 3; reasons.append('5m温和放量'+str(round(vr,1))+'x')
        except Exception: pass

        # === 门槛降到10 (更早进入) ===
        sig = 'long' if score >= 10 else ('short' if score <= -10 else 'wait')
        return {'sym': sym, 'signal': sig, 'score': score, 'price': price,
            'reasons': reasons, 'cvd': round(cv,1), 'rsi': round(rs,0), 'trend': trend_1h}
    except Exception as e:
        return None'''

content = content.replace(old_analyze, new_analyze)

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.write(content)
import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('OK: yaobi v9 multi-timeframe + acceleration + squeeze')
