import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Use exact text
old_block = """        # ?????(????)
        try:
            lsr = fetch_long_short_ratio(sym)
            if lsr > 2.5: score -= 6; reasons.append('??????')
            elif lsr < 0.5: score += 6; reasons.append('??????')
        except Exception: pass

        # ??????"""

new_block = """        # ?????(????)
        try:
            lsr = fetch_long_short_ratio(sym)
            if lsr > 2.5: score -= 6; reasons.append('??????')
            elif lsr < 0.5: score += 6; reasons.append('??????')
        except Exception: pass

        # ??????
        try:
            ob = fetch_orderbook_imbalance(sym)
            if ob:
                imb = ob.get('imbalance', 0)
                if imb > 15: score += 8; reasons.append('?????')
                elif imb < -15: score -= 8; reasons.append('?????')
        except Exception: pass

        # 1m??CVD
        try:
            cvd1m = fetch_1m_cvd(sym)
            if abs(cvd1m) > 15:
                if cvd1m > 15: score += 10; reasons.append('1m??')
                else: score -= 10; reasons.append('1m??')
        except Exception: pass

        # ?????
        try:
            tape = fetch_tape_pressure(sym)
            if tape:
                lp = tape.get('large_net', 0)
                if abs(lp) >= 2:
                    if lp > 0: score += 6; reasons.append('????')
                    else: score -= 6; reasons.append('????')
        except Exception: pass

        # ??????"""

content = content.replace(old_block, new_block)
print('Yaobi: 3 new leading signals added')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('yaobi_v8.py: compiled OK')
