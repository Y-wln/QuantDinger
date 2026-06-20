#!/usr/bin/env python3
"""Fix yaobi_v8.py - replace all corrupted Chinese with proper characters"""
import re

with open("/home/ubuntu/scripts/yaobi_v8.py", "r", encoding="utf-8") as f:
    content = f.read()

replacements = [
    # Docstring
    ('"""???? - 1h + CVD + RSI + 5m??"""', '"""妖币分析 - 1h趋势 + CVD量 + RSI + 5m放量"""'),
    # CVD reasons
    ("'CVD??'+str(int(cv))+'%'", "'CVD多头'+str(int(cv))+'%'"),
    ("'CVD??'+str(int(cv))+'%'", "'CVD空头'+str(int(cv))+'%'"),
    # ... but they have duplicates for >20, <-20, >10, <-10
    # Let me be more surgical
]

# Simpler approach: direct line-by-line replacement
lines = content.split('\n')
new_lines = []
for line in lines:
    # CVD多头/空头 reasons
    if "CVD??'+str(int(cv))+'%'" in line:
        if "cv > 20" in line or "cv > 10" in line:
            line = line.replace("CVD??'+str(int(cv))+'%'", "CVD多头'+str(int(cv))+'%'")
        elif "cv < -20" in line or "cv < -10" in line:
            line = line.replace("CVD??'+str(int(cv))+'%'", "CVD空头'+str(int(cv))+'%'")
    # RSI reasons  
    if "RSI??'+str(int(rs))" in line:
        if "rs < 25" in line or "rs < 35" in line:
            line = line.replace("RSI??'+str(int(rs))", "RSI超卖'+str(int(rs))")
        elif "rs > 75" in line or "rs > 65" in line:
            line = line.replace("RSI??'+str(int(rs))", "RSI超买'+str(int(rs))")
    # Trend reasons
    if "'????'" in line:
        if "trend == 'up'" in line:
            line = line.replace("'????'", "'趋势向上'")
        elif "trend == 'down'" in line:
            line = line.replace("'????'", "'趋势向下'")
    # 5m volume
    if "'5m??'" in line:
        line = line.replace("'5m??'+str(round(vr,1))+'x'", "'5m放量'+str(round(vr,1))+'x'")
    if "'5m???'" in line:
        line = line.replace("'5m???'+str(round(vr,1))+'x'", "'5m微放量'+str(round(vr,1))+'x'")
    # Report headers
    if '"??????????????????"' in line:
        line = line.replace('"??????????????????"', '"━━━━━━━━━━━━━━━━"')
    if '"  ?? ???? | "' in line:
        line = line.replace('"  ?? ???? | "', '"  🎯 妖币信号 | "')
    if '"??????????????????"' in line and 'report' in line:
        pass  # already handled
    # Long section header
    if '"  ?? ????"' in line:
        line = line.replace('"  ?? ????"', '"  🟢 做多信号"')
    # Short section header  
    if '"  ?? ????"' in line:
        line = line.replace('"  ?? ????"', '"  🔴 做空信号"')
    # Individual signal line
    if '"    ?? {:<6} {:>3}? CVD{:>6}% RSI{:>3} ${}"' in line:
        line = line.replace('"    ?? {:<6} {:>3}? CVD{:>6}% RSI{:>3} ${}"', '"    {:<6} {:>3}分 CVD{:>6}% RSI{:>3} ${}"')
    # Closed section header
    if '"  ?? ????"' in line:
        line = line.replace('"  ?? ????"', '"  📋 平仓记录"')
    # Closed emoji
    if 'em = "?" if pnl > 0 else "?"' in line:
        line = line.replace('em = "?" if pnl > 0 else "?"', 'em = "✅" if pnl > 0 else "❌"')
    # Position direction label
    if 'd = "?" if p["direction"] == "long" else "?"' in line:
        line = line.replace('d = "?" if p["direction"] == "long" else "?"', 'd = "多" if p["direction"] == "long" else "空"')
    # Stop loss / take profit labels
    if "'??'" in line and 'closed.append' in line:
        if "price <= p['sl']" in line:
            line = line.replace("'??'", "'止损'")
        elif "price >= p['tp']" in line:
            line = line.replace("'??'", "'止盈'")
        elif "price >= p['sl']" in line:
            line = line.replace("'??'", "'止损'")
        elif "price <= p['tp']" in line:
            line = line.replace("'??'", "'止盈'")
    # Comment lines
    if '# ?8??????' in line:
        line = line.replace('# ?8??????', '# 最多8个持仓')
    if '# ??????????' in line:
        line = line.replace('# ??????????', '# 发送飞书报告')
    if '# ????/??' in line:
        line = line.replace('# ????/??', '# 止盈/止损')
    # pos_str empty
    if '"??"' in line and 'pos_str' in line:
        line = line.replace('"??"', '"空仓"')
    # Section close
    if '"??????????????????"' in line:
        line = line.replace('"??????????????????"', '"━━━━━━━━━━━━━━━━"')
    # Signal emoji prefix in report
    if 'report.append("    {} {:<6} {} ??:{:+.1f}%".format(em, cn, reason, pnl))' in line:
        line = line.replace('report.append("    {} {:<6} {} ??:{:+.1f}%".format(em, cn, reason, pnl))',
                           'report.append("    {} {:<6} {} 盈亏:{:+.1f}%".format(em, cn, reason, pnl))')

    new_lines.append(line)

with open("/home/ubuntu/scripts/yaobi_v8.py", "w", encoding="utf-8") as f:
    f.write('\n'.join(new_lines))

import py_compile
py_compile.compile("/home/ubuntu/scripts/yaobi_v8.py", doraise=True)
print("yaobi_v8.py Chinese fix applied OK")
