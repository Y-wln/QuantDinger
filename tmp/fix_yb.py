import sys

with open("/home/ubuntu/scripts/yaobi_v8.py", "r") as f:
    code = f.read()

old_analyze = """def analyze_one(sym):
    \"\"\"???? ? 1h K? + CVD + RSI\"\"\"
    try:
        k1 = fetch_klines(sym, '1h', 100)
        if len(k1) < 50: return None
        c = [k['c'] for k in k1]
        rs = rsi(c)
        cv = calc_cvd(k1, 6)
        e20 = ema(c, 20)
        e50 = ema(c, 50)
        price = c[-1]
        trend = 'up' if price > e20 > e50 else ('down' if price < e20 < e50 else 'neutral')
        sig = None
        score = 0
        reasons = []

        # CVD??
        if cv > 30: score += 15; reasons.append('CVD??'+str(int(cv))+'%'); sig = 'long'
        elif cv < -30: score -= 15; reasons.append('CVD??'+str(int(cv))+'%'); sig = 'short'
        # RSI
        if rs < 30: score += 10; reasons.append('RSI??'+str(int(rs)))
        elif rs > 70: score -= 10; reasons.append('RSI??'+str(int(rs)))
        # ??
        if trend == 'up': score += 8
        elif trend == 'down': score -= 8

        if abs(score) >= 15:
            sig = 'long' if score > 0 else 'short'
            return {'sym': sym, 'signal': sig, 'score': score, 'price': price,
                'reasons': reasons, 'cvd': round(cv,1), 'rsi': rs, 'trend': trend}
        return None
    except:
        return None"""

new_analyze = """def analyze_one(sym):
    \"\"\"???? ? 1h K? + CVD + RSI + 5m??\"\"\"
    try:
        k1 = fetch_klines(sym, '1h', 100)
        if len(k1) < 50: return None
        c = [k['c'] for k in k1]
        rs_arr = rsi(c)
        rs = rs_arr[-1] if isinstance(rs_arr, list) and rs_arr else 50
        cv = calc_cvd(k1, 6)
        e20_arr = ema(c, 20)
        e50_arr = ema(c, 50)
        e20 = (e20_arr[-1] if isinstance(e20_arr, list) and e20_arr else c[-1])
        e50 = (e50_arr[-1] if isinstance(e50_arr, list) and e50_arr else c[-1])
        price = c[-1]
        trend = 'up' if price > e20 > e50 else ('down' if price < e20 < e50 else 'neutral')
        score = 0
        reasons = []

        # CVD?? (?????, ????)
        if cv > 20: score += 12; reasons.append('CVD??'+str(int(cv))+'%')
        elif cv < -20: score -= 12; reasons.append('CVD??'+str(int(cv))+'%')
        elif cv > 10: score += 6; reasons.append('CVD??'+str(int(cv))+'%')
        elif cv < -10: score -= 6; reasons.append('CVD??'+str(int(cv))+'%')
        # RSI (??RSI???, ??)
        if rs < 25: score += 12; reasons.append('RSI??'+str(int(rs)))
        elif rs < 35: score += 6; reasons.append('RSI??'+str(int(rs)))
        elif rs > 75: score -= 12; reasons.append('RSI??'+str(int(rs)))
        elif rs > 65: score -= 6; reasons.append('RSI??'+str(int(rs)))
        # ??
        if trend == 'up': score += 8; reasons.append('????')
        elif trend == 'down': score -= 8; reasons.append('????')
        # 5m???? (??????)
        try:
            k5 = fetch_klines(sym, '5m', 30)
            if k5 and len(k5) >= 10:
                v5 = [k['v'] for k in k5]
                avg5 = sum(v5[-9:-1]) / 8 if len(v5) >= 9 else 1
                if avg5 > 0:
                    vr = v5[-1] / avg5
                    if vr > 2.0:
                        score += 8; reasons.append('5m??'+str(round(vr,1))+'x')
                    elif vr > 1.5:
                        score += 4; reasons.append('5m???'+str(round(vr,1))+'x')
        except Exception: pass

        sig = 'long' if score >= 12 else ('short' if score <= -12 else 'wait')
        return {'sym': sym, 'signal': sig, 'score': score, 'price': price,
            'reasons': reasons, 'cvd': round(cv,1), 'rsi': round(rs,0), 'trend': trend}
    except Exception as e:
        return None"""

code = code.replace(old_analyze, new_analyze)

# Also fix the alert threshold (was not changed properly)
code = code.replace("if s['score'] >= 25:", "if s['score'] >= 12:")
code = code.replace("elif s['score'] <= -25:", "elif s['score'] <= -12:")

# Fix signal collection (use analyze_one's new threshold)
old_collect = "                if r: signals.append(r)"
new_collect = "                if r and r.get('signal') != 'wait': signals.append(r)"
code = code.replace(old_collect, new_collect)

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.write(code)

import py_compile
py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
print("yaobi_v8 fix OK - EMA/RSI indexing + lower thresholds")
