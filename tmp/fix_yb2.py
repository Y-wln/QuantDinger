import sys

with open("/home/ubuntu/scripts/yaobi_v8.py", "r") as f:
    code = f.read()

# Find and replace analyze_one using line-based approach
lines = code.split("\n")
in_func = False
func_start = -1
func_end = -1
brace_depth = 0

for i, line in enumerate(lines):
    if line.strip().startswith("def analyze_one"):
        func_start = i
        in_func = True
        continue
    if in_func:
        if line.strip().startswith("def ") or line.strip().startswith("class "):
            func_end = i
            break
        if i == len(lines) - 1:
            func_end = i + 1

if func_start < 0:
    print("ERROR: analyze_one not found")
    sys.exit(1)

# Auto-detect end of function (next def or end of file)
for i in range(func_start + 1, len(lines)):
    if lines[i].strip().startswith("def ") or lines[i].strip().startswith("class "):
        func_end = i
        break
if func_end < 0:
    func_end = len(lines)

print(f"analyze_one at lines {func_start+1}-{func_end}")

new_func = '''def analyze_one(sym):
    """???? - 1h + CVD + RSI + 5m??"""
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
        if cv > 20: score += 12; reasons.append('CVD??'+str(int(cv))+'%')
        elif cv < -20: score -= 12; reasons.append('CVD??'+str(int(cv))+'%')
        elif cv > 10: score += 6; reasons.append('CVD??'+str(int(cv))+'%')
        elif cv < -10: score -= 6; reasons.append('CVD??'+str(int(cv))+'%')
        # RSI (?????)
        if rs < 25: score += 12; reasons.append('RSI??'+str(int(rs)))
        elif rs < 35: score += 6; reasons.append('RSI??'+str(int(rs)))
        elif rs > 75: score -= 12; reasons.append('RSI??'+str(int(rs)))
        elif rs > 65: score -= 6; reasons.append('RSI??'+str(int(rs)))
        # ??
        if trend == 'up': score += 8; reasons.append('????')
        elif trend == 'down': score -= 8; reasons.append('????')
        # 5m??
        try:
            k5 = fetch_klines(sym, '5m', 30)
            if k5 and len(k5) >= 10:
                v5 = [k['v'] for k in k5]
                avg5 = sum(v5[-9:-1]) / 8 if len(v5) >= 9 else 1
                if avg5 > 0:
                    vr = v5[-1] / avg5
                    if vr > 2.0: score += 8; reasons.append('5m??'+str(round(vr,1))+'x')
                    elif vr > 1.5: score += 4; reasons.append('5m???'+str(round(vr,1))+'x')
        except Exception: pass

        sig = 'long' if score >= 12 else ('short' if score <= -12 else 'wait')
        return {'sym': sym, 'signal': sig, 'score': score, 'price': price,
            'reasons': reasons, 'cvd': round(cv,1), 'rsi': round(rs,0), 'trend': trend}
    except Exception as e:
        return None'''

new_lines = new_func.split("\n")
result_lines = lines[:func_start] + new_lines + lines[func_end:]

code = "\n".join(result_lines)

# Also fix signal collection and alert threshold
code = code.replace("if s['score'] >= 18:", "if s['score'] >= 12:")
code = code.replace("elif s['score'] <= -18:", "elif s['score'] <= -12:")

# Ensure signal collection uses the new threshold
code = code.replace(
    "if r and r.get('signal') != 'wait': signals.append(r)",
    "if r and r.get('signal') != 'wait': signals.append(r)"
)

with open("/home/ubuntu/scripts/yaobi_v8.py", "w") as f:
    f.write(code)

import py_compile
py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
print("yaobi_v8.py FIXED with line-based replacement + compiles OK")
