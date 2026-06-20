import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')

# ====== 1. agent_technical.py ???? ======
with open('/home/ubuntu/scripts/agents/agent_technical.py', 'r', encoding='utf-8') as f:
    content = f.read()

changes = []

# 1.1 ????/????? -15/+15 ?? -8/+8?????????5m???????
old = "            score -= 15\n            details['trend_follow'] = '-15"
new = "            score -= 8\n            details['trend_follow'] = '-8"
if old in content:
    content = content.replace(old, new)
    changes.append('trend_follow: -15->-8')
else:
    print('WARN: trend_follow -15 not found')

old = "            score += 15\n            details['trend_follow'] = '+15"
new = "            score += 8\n            details['trend_follow'] = '+8"
if old in content:
    content = content.replace(old, new)
    changes.append('trend_follow: +15->+8')

# 1.2 ????? -10/-8 ?? -5/-4
old = "                score -= 10\n                details['pullback']"
new = "                score -= 5\n                details['pullback']"
if old in content:
    content = content.replace(old, new)
    changes.append('pullback_short: -10->-5')

old = "                score += 10\n                details['pullback']"
new = "                score += 5\n                details['pullback']"
if old in content:
    content = content.replace(old, new)
    changes.append('pullback_long: +10->+5')

# 1.3 ???????? +15 ?? +20
old = "                    score += 15; details['launch_boost'] = '+15 5m??+????(????)'"
new = "                    score += 20; details['launch_boost'] = '+20 5m??+????(????)'"
if old in content:
    content = content.replace(old, new)
    changes.append('launch_boost: +15->+20')

# 1.4 ????? +5 ?? +8
old = "                    score += 5; details['launch_reverse'] = '+5 5m??(??????)'"
new = "                    score += 8; details['launch_reverse'] = '+8 5m??(??????)'"
if old in content:
    content = content.replace(old, new)
    changes.append('launch_reverse: +5->+8')

# 1.5 ????? 25 ?? 18??????
old = "    signal = 'long' if score >= 25 else ('short' if score <= -25 else 'wait')"
new = "    signal = 'long' if score >= 18 else ('short' if score <= -18 else 'wait')"
if old in content:
    content = content.replace(old, new)
    changes.append('signal_threshold: 25->18')

# 1.6 ??3???????technical??????orch?
# ????????????????
old_marker = "        # ====== ????? - ????? (30?) ======"
new_marker = """        # ====== ?????? (????) ======
        try:
            from hermes_core import fetch_orderbook_imbalance, fetch_1m_cvd, fetch_tape_pressure
            ob = fetch_orderbook_imbalance(symbol)
            if ob:
                imb = ob.get('imbalance', 0)
                if imb > 15:
                    score += 8; details['orderbook'] = '+8 ?????(' + str(imb) + '%)'
                    leading_signals.append('???????')
                elif imb < -15:
                    score -= 8; details['orderbook'] = '-8 ?????(' + str(imb) + '%)'
                    leading_signals.append('???????')
            cvd1m = fetch_1m_cvd(symbol)
            if abs(cvd1m) > 15:
                if cvd1m > 15:
                    score += 10; details['cvd1m'] = '+10 1mCVD??(' + str(int(cvd1m)) + '%)'
                    leading_signals.append('1mCVD??')
                else:
                    score -= 10; details['cvd1m'] = '-10 1mCVD??(' + str(int(cvd1m)) + '%)'
                    leading_signals.append('1mCVD??')
            tape = fetch_tape_pressure(symbol)
            if tape:
                lp = tape.get('large_net', 0)
                if abs(lp) >= 3:
                    if lp > 0:
                        score += 6; details['tape'] = '+6 ????(' + str(lp) + ')'
                    else:
                        score -= 6; details['tape'] = '-6 ????(' + str(lp) + ')'
        except Exception:
            pass

        # ====== ????? - ????? (30?) ======"""

if old_marker in content:
    content = content.replace(old_marker, new_marker)
    changes.append('leading_indicators: added to technical')
else:
    print('WARN: old_marker not found')

content = content.replace("v3 - SMC+launch+patterns+divergence", "v4 - fast entry(18)+leading(orderbook/1mCVD/tape)")
content = content.replace("[AgentTechnical] v3", "[AgentTechnical] v4")

with open('/home/ubuntu/scripts/agents/agent_technical.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/agent_technical.py', doraise=True)
print('agent_technical.py: OK')
print('Changes:', changes)

# ====== 2. agent_orchestrator.py ???? ======
with open('/home/ubuntu/scripts/agents/agent_orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'SIGNAL_THRESHOLD = 35'
new = 'SIGNAL_THRESHOLD = 28'
if old in content:
    content = content.replace(old, new)
    print('orch SIGNAL_THRESHOLD: 35->28')

old = "v30.19 starting (OI+taker+LSR+funding+FnG)..."
new = "v31.0 fast (thresh28+leading+5mBoost) starting..."
if old in content:
    content = content.replace(old, new)

old = "Hermes v30.19 | OI+taker+LSR+FR+FnG"
new = "Hermes v31 | OI+taker+LSR+FR+FnG+???+1mCVD+???"
if old in content:
    content = content.replace(old, new)

with open('/home/ubuntu/scripts/agents/agent_orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

py_compile.compile('/home/ubuntu/scripts/agents/agent_orchestrator.py', doraise=True)
print('agent_orchestrator.py: OK')

print('\nDone! agent_technical v4 + orch v31')
