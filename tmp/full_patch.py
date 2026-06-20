# -*- coding: utf-8 -*-
import sys, json, py_compile

# ============================================
# PATCH 1: hermes_core.py - Add CVD snap + faster launch
# ============================================
with open('/home/ubuntu/scripts/agents/hermes_core.py', 'r') as f:
    code = f.read()

cvd_snap_func = '''
# ====== CVD???? (??????) ======
def cvd_snap_detect(klines_5m, window=6):
    """??15???CVD????"""
    if not klines_5m or len(klines_5m) < window + 3:
        return {"direction": "none", "bonus": 0, "snap_pct": 0}
    try:
        closes = [k["c"] for k in klines_5m]
        vols = [k["v"] for k in klines_5m]
        buys, sells = 0, 0
        for i in range(len(closes)):
            if closes[i] >= (closes[i-1] if i > 0 else closes[i]):
                buys += vols[i]
            else:
                sells += vols[i]
        if buys + sells == 0:
            return {"direction": "none", "bonus": 0, "snap_pct": 0}
        cvd_now = (buys - sells) / (buys + sells) * 100
        b2, s2 = 0, 0
        for i in range(-window-3, -3):
            if i >= -len(closes):
                if closes[i] >= closes[i-1]:
                    b2 += vols[i]
                else:
                    s2 += vols[i]
        if b2 + s2 == 0:
            return {"direction": "none", "bonus": 0, "snap_pct": 0}
        cvd_prev = (b2 - s2) / (b2 + s2) * 100
        snap = cvd_now - cvd_prev
        if snap > 30:
            return {"direction": "long", "bonus": 15, "snap_pct": round(snap, 1)}
        elif snap < -30:
            return {"direction": "short", "bonus": 15, "snap_pct": round(snap, 1)}
        elif snap > 15:
            return {"direction": "long", "bonus": 8, "snap_pct": round(snap, 1)}
        elif snap < -15:
            return {"direction": "short", "bonus": 8, "snap_pct": round(snap, 1)}
    except Exception:
        pass
    return {"direction": "none", "bonus": 0, "snap_pct": 0}
'''

insert_pos = code.find('def detect_launch(')
if insert_pos > 0 and 'def cvd_snap_detect(' not in code:
    code = code[:insert_pos] + cvd_snap_func + code[insert_pos:]
    print('[OK] CVD snap detection added to hermes_core')
else:
    print('[SKIP] CVD snap already exists')

# Lower launch thresholds (12 bars instead of 22, 1.3x instead of 1.5x)
code = code.replace('len(klines_5m) >= 22:', 'len(klines_5m) >= 12:')
code = code.replace("sum(v5[-21:-1]) / 20", "sum(v5[-11:-1]) / 10")
code = code.replace("sum(v5[-21:-1])/20", "sum(v5[-11:-1])/10")
code = code.replace("if vr > 3.0:\n                bonus += 3; strong = 3; signals.append('5m??'", "if vr > 2.5:\n                bonus += 3; strong = 3; signals.append('5m??'")
code = code.replace("if vr > 2.0:\n                bonus += 2; strong = 2; signals.append('5m??'", "if vr > 1.8:\n                bonus += 2; strong = 2; signals.append('5m??'")
code = code.replace("if vr > 1.5:\n                bonus += 1; strong = max(strong, 1); signals.append('5m???'", "if vr > 1.3:\n                bonus += 1; strong = max(strong, 1); signals.append('5m???'")

# Higher launch max bonus
code = code.replace('bonus = max(-5, min(8, bonus))', 'bonus = max(-8, min(15, bonus))')

with open('/home/ubuntu/scripts/agents/hermes_core.py', 'w') as f:
    f.write(code)
print('[OK] hermes_core.py patched')

# ============================================
# PATCH 2: agent_technical.py
# ============================================
with open('/home/ubuntu/scripts/agents/agent_technical.py', 'r') as f:
    code2 = f.read()

# Add CVD snap import
code2 = code2.replace(
    'from hermes_core import (ema, rsi, atr, macd, supertrend, calc_cvd,',
    'from hermes_core import (ema, rsi, atr, macd, supertrend, calc_cvd, cvd_snap_detect,'
)

# Add CVD snap scoring before Bollinger
old_bb = '# ====== ??? (8?) ======'
new_cvd_block = '''        # ====== CVD?? (12?, ????) ======
        if klines_5m and len(klines_5m) >= 9:
            snap = cvd_snap_detect(klines_5m, 6)
            if snap["bonus"] > 0:
                score += snap["bonus"]
                details["cvd_snap"] = "+" + str(snap["bonus"]) + " CVD??" + str(snap["snap_pct"]) + "%"
                leading_signals.append("CVD????(" + str(snap["snap_pct"]) + "%)")
            elif snap["bonus"] < 0:
                score += snap["bonus"]
                details["cvd_snap"] = str(snap["bonus"]) + " CVD??" + str(snap["snap_pct"]) + "%"
                leading_signals.append("CVD????(" + str(snap["snap_pct"]) + "%)")

        # ====== ??? (8?) ======'''
code2 = code2.replace(old_bb, new_cvd_block)

# Stronger trend override
code2 = code2.replace(
    "if trend_down:\n                score += 3; details['fng'] = '+3 ???????(??)'",
    "if trend_down:\n                score -= 5; details['fng'] = '-5 ?????????=????'"
)
code2 = code2.replace(
    "if trend_up:\n                score -= 3; details['fng'] = '-3 ???????(??)'",
    "if trend_up:\n                score += 5; details['fng'] = '+5 ?????????=????'"
)
code2 = code2.replace(
    "if trend_down:\n                score += 1; details['fng'] = '+1 ???????(??)'",
    "if trend_down:\n                score += 0; details['fng'] = '0 ???????(???)'"
)
code2 = code2.replace(
    "if trend_up:\n                score -= 1; details['fng'] = '-1 ???????(??)'",
    "if trend_up:\n                score += 0; details['fng'] = '0 ???????(???)'"
)

# Add funding rate extreme before signal determination
old_sig = "# ====== ???? ======"
new_fr_block = '''        # ====== ???????? ======
        try:
            fr = fetch_funding_rate(symbol) if symbol else 0
            if isinstance(fr, (int, float)) and abs(fr) > 0:
                if fr < -0.0005:
                    score += 8; details["fr_signal"] = "+8 ????(??)"
                    leading_signals.append("??-" + str(round(abs(fr)*100,3)) + "% ??")
                elif fr > 0.0005:
                    score -= 8; details["fr_signal"] = "-8 ????(??)"
                    leading_signals.append("??+" + str(round(fr*100,3)) + "% ??")
        except Exception: pass

        # ====== ???? ======'''
code2 = code2.replace(old_sig, new_fr_block)

with open('/home/ubuntu/scripts/agents/agent_technical.py', 'w') as f:
    f.write(code2)

print('[OK] agent_technical.py patched')

# Compile check
try:
    py_compile.compile('/home/ubuntu/scripts/agents/hermes_core.py', doraise=True)
    print('[OK] hermes_core compiles')
except py_compile.PyCompileError as e:
    print('[ERROR] hermes_core: ' + str(e))

try:
    py_compile.compile('/home/ubuntu/scripts/agents/agent_technical.py', doraise=True)
    print('[OK] agent_technical compiles')
except py_compile.PyCompileError as e:
    print('[ERROR] agent_technical: ' + str(e))

print('\n=== ALL PATCHES DONE ===')
