import sys

with open("/home/ubuntu/scripts/yaobi_v8.py", "r") as f:
    code = f.read()

# Lower signal threshold from 20 to 15
code = code.replace("if abs(score) >= 20:", "if abs(score) >= 15:")

# Lower alert threshold from 25 to 18
code = code.replace("if s['score'] >= 25:", "if s['score'] >= 18:")
code = code.replace("elif s['score'] <= -25:", "elif s['score'] <= -18:")

# Use hermes_core CVD snap for faster detection
old_analysis = """        # CVD??
        if cv > 30: score += 15; reasons.append('CVD??'+str(int(cv))+'%'); sig = 'long'
        elif cv < -30: score -= 15; reasons.append('CVD??'+str(int(cv))+'%'); sig = 'short'
        # RSI
        if rs < 30: score += 10; reasons.append('RSI??'+str(int(rs)))
        elif rs > 70: score -= 10; reasons.append('RSI??'+str(int(rs)))
        # ??
        if trend == 'up': score += 8
        elif trend == 'down': score -= 8"""

new_analysis = """        # CVD?? (????, ????)
        if cv > 20: score += 12; reasons.append('CVD??'+str(int(cv))+'%'); sig = 'long'
        elif cv < -20: score -= 12; reasons.append('CVD??'+str(int(cv))+'%'); sig = 'short'
        elif cv > 10: score += 6; reasons.append('CVD??'+str(int(cv))+'%')
        elif cv < -10: score -= 6; reasons.append('CVD??'+str(int(cv))+'%')
        # RSI
        if rs < 25: score += 12; reasons.append('RSI??'+str(int(rs)))
        elif rs < 35: score += 6; reasons.append('RSI??'+str(int(rs)))
        elif rs > 75: score -= 12; reasons.append('RSI??'+str(int(rs)))
        elif rs > 65: score -= 6; reasons.append('RSI??'+str(int(rs)))
        # ??
        if trend == 'up': score += 8; reasons.append('????')
        elif trend == 'down': score -= 8; reasons.append('????')
        # 5m????
        try:
            k5 = fetch_klines(sym, '5m', 30)
            if k5 and len(k5) >= 10:
                v5 = [k['v'] for k in k5]
                avg5 = sum(v5[-9:-1]) / 8 if len(v5) >= 9 else 1
                if avg5 > 0:
                    vr = v5[-1] / avg5
                    if vr > 2.0:
                        score += 6; reasons.append('5m??'+str(round(vr,1))+'x')
                        if sig != 'short': sig = 'long'
                    elif vr < 0.3:
                        score -= 6; reasons.append('5m??'+str(round(vr,1))+'x')
        except Exception: pass"""

code = code.replace(old_analysis, new_analysis)

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.write(code)

import py_compile
py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
print("yaobi_v8 patched OK")
