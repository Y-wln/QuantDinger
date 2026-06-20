import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/agents/agent_technical.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix launch_boost (line 176)
for i, line in enumerate(lines):
    if "launch_boost" in line and "+15" in line:
        lines[i] = line.replace("+15", "+20")
        print(f'Line {i+1}: launch_boost +15->+20')
    if "launch_reverse" in line and "+5" in line:
        lines[i] = line.replace("+5", "+8")
        print(f'Line {i+1}: launch_reverse +5->+8')

# Insert leading indicators before launch detection
leading_block = """        # ====== ?????? (????) ======
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

"""

inserted = False
new_lines = []
for i, line in enumerate(lines):
    if '# ====== ?????' in line and not inserted:
        new_lines.append(leading_block)
        inserted = True
    new_lines.append(line)

with open('/home/ubuntu/scripts/agents/agent_technical.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/agent_technical.py', doraise=True)
print('agent_technical.py: v4 complete (leading indicators inserted)')
