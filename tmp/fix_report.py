import sys
p = '/home/ubuntu/scripts/yaobi_v8.py' if len(sys.argv) < 2 else sys.argv[1]
with open(p) as f:
    code = f.read()

# Fix 1: max_workers 5->10
code = code.replace('max_workers=5', 'max_workers=10')

# Fix 2: Update alert format to include top reasons
old_alert = 'alerts.append("LONG|" + sym + "|" + str(s["score"]) + "|" + str(round(s["cvd"],1)) + "|" + str(int(s["rsi"])) + "|" + str(round(s["price"],4)))'
new_alert = 'top_reasons = " | ".join(s.get("reasons",[])[:3]) if s.get("reasons") else ""\n            alerts.append("LONG|" + sym + "|" + str(s["score"]) + "|" + str(round(s["cvd"],1)) + "|" + str(int(s["rsi"])) + "|" + str(round(s["price"],4)) + "|" + top_reasons)'
code = code.replace(old_alert, new_alert)

# Fix both short/long alerts (same pattern for add alert)
# The alert format now has 7 fields: TYPE|SYM|SCORE|CVD|RSI|PRICE|REASONS

# Fix 3: Update report display to show reasons
old_long = '            report.append("  \U0001f7e2 \u505a\u591a\u4fe1\u53f7")\n            for a in longs[:5]:\n                parts = a.split("|")\n                if len(parts) >= 6:\n                    _, nm, sc, cv, rs, pr = parts\n                    cn = nm.replace("USDT","")\n                    report.append("    {:<6} {:>3}\u5206 CVD{:>6}% RSI{:>3} ${}".format(cn, sc, cv, rs, pr))'

new_long = '            report.append("  \U0001f7e2 \u505a\u591a\u4fe1\u53f7")\n            for a in longs[:5]:\n                parts = a.split("|")\n                if len(parts) >= 6:\n                    nm = parts[0]; sc = parts[1]; cv = parts[2]; rs = parts[3]; pr = parts[4]\n                    reasons = parts[5] if len(parts) >= 7 else ""\n                    cn = nm.replace("USDT","")\n                    report.append("    {:<6} {:>3}\u5206 CVD{:>6}% RSI{:>3} ${}".format(cn, sc, cv, rs, pr))\n                    if reasons:\n                        report.append("      \u2192 {}".format(reasons))'

code = code.replace(old_long, new_long)

# Fix 4: Same for shorts
old_short = '            report.append("  \U0001f534 \u505a\u7a7a\u4fe1\u53f7")\n            for a in shorts[:5]:\n                parts = a.split("|")\n                if len(parts) >= 6:\n                    _, nm, sc, cv, rs, pr = parts\n                    cn = nm.replace("USDT","")\n                    report.append("    {:<6} {:>3}\u5206 CVD{:>6}% RSI{:>3} ${}".format(cn, sc, cv, rs, pr))'

new_short = '            report.append("  \U0001f534 \u505a\u7a7a\u4fe1\u53f7")\n            for a in shorts[:5]:\n                parts = a.split("|")\n                if len(parts) >= 6:\n                    nm = parts[0]; sc = parts[1]; cv = parts[2]; rs = parts[3]; pr = parts[4]\n                    reasons = parts[5] if len(parts) >= 7 else ""\n                    cn = nm.replace("USDT","")\n                    report.append("    {:<6} {:>3}\u5206 CVD{:>6}% RSI{:>3} ${}".format(cn, sc, cv, rs, pr))\n                    if reasons:\n                        report.append("      \u2192 {}".format(reasons))'

code = code.replace(old_short, new_short)

# Fix 5: update version
for old_v in ['v15', 'v14', 'v13', 'v12']:
    if old_v in code:
        code = code.replace(old_v, 'v16')
        break

with open(p, 'w') as f:
    f.write(code)

import py_compile
py_compile.compile(p, doraise=True)
print('syntax OK, lines:', len(code.split(chr(10))))
