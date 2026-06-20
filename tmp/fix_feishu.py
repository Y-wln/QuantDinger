with open("/home/ubuntu/scripts/agents/feishu_callback.py") as f:
    content = f.read()

# Find the analyze_one function in handle_yaobi_scan
old_analyze = """        def analyze_one(sym):
            try:
                k1 = fetch_klines(sym, '1h', 100)
                if len(k1) < 50: return None
                c = [k['c'] for k in k1]
                rs = rsi(c); cv = calc_cvd(k1, 6)
                e20 = ema(c, 20); e50 = ema(c, 50)
                price = c[-1]
                trend = 'up' if price > e20 > e50 else ('down' if price < e20 < e50 else 'neutral')
                score = 0; reasons = []
                if cv > 30: score += 15; reasons.append('CVD??'+str(int(cv))+'%')
                elif cv < -30: score -= 15; reasons.append('CVD??'+str(int(cv))+'%')
                if rs < 30: score += 10; reasons.append('RSI??'+str(int(rs)))
                elif rs > 70: score -= 10; reasons.append('RSI??'+str(int(rs)))
                if trend == 'up': score += 8
                elif trend == 'down': score -= 8
                if abs(score) >= 20:
                    return {'sym':sym,'signal':'long' if score>0 else 'short','score':score,
                        'price':price,'reasons':reasons,'cvd':round(cv,1),'rsi':rs,'trend':trend}
            except Exception: pass
            return None"""

new_analyze = """        def analyze_one(sym):
            try:
                k1 = fetch_klines(sym, '1h', 100)
                if len(k1) < 50: return None
                c = [k['c'] for k in k1]
                rs_arr = rsi(c)
                rs = float(rs_arr[-1]) if isinstance(rs_arr, list) and len(rs_arr) > 0 else 50
                cv = calc_cvd(k1, 6)
                e20_arr = ema(c, 20); e50_arr = ema(c, 50)
                e20 = float(e20_arr[-1]) if isinstance(e20_arr, list) and len(e20_arr) > 0 else c[-1]
                e50 = float(e50_arr[-1]) if isinstance(e50_arr, list) and len(e50_arr) > 0 else c[-1]
                price = c[-1]
                trend = 'up' if price > e20 and e20 > e50 else ('down' if price < e20 and e20 < e50 else 'neutral')
                score = 0; reasons = []
                if cv > 20: score += 12; reasons.append('CVD??'+str(int(cv))+'%')
                elif cv < -20: score -= 12; reasons.append('CVD??'+str(int(cv))+'%')
                elif cv > 10: score += 6; reasons.append('CVD??'+str(int(cv))+'%')
                elif cv < -10: score -= 6; reasons.append('CVD??'+str(int(cv))+'%')
                if rs < 25: score += 12; reasons.append('RSI??'+str(int(rs)))
                elif rs < 35: score += 6; reasons.append('RSI??'+str(int(rs)))
                elif rs > 75: score -= 12; reasons.append('RSI??'+str(int(rs)))
                elif rs > 65: score -= 6; reasons.append('RSI??'+str(int(rs)))
                if trend == 'up': score += 8; reasons.append('????')
                elif trend == 'down': score -= 8; reasons.append('????')
                if abs(score) >= 12:
                    return {'sym':sym,'signal':'long' if score>0 else 'short','score':score,
                        'price':price,'reasons':reasons,'cvd':round(cv,1),'rsi':round(rs,0),'trend':trend}
            except Exception as e:
                pass
            return None"""

if old_analyze in content:
    content = content.replace(old_analyze, new_analyze)
    print("Feishu analyze_one FIXED")
else:
    print("FAIL - pattern not found")

with open("/home/ubuntu/scripts/agents/feishu_callback.py", "w") as f:
    f.write(content)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/agents/feishu_callback.py", doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print("ERROR: " + str(e))
