import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add imports for new leading signals
old_import = 'from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands, atr,'
new_import = '''from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands, atr,
    fetch_orderbook_imbalance, fetch_1m_cvd, fetch_tape_pressure,'''
content = content.replace(old_import, new_import)
print('Imports: updated')

# 2. Add 3 new leading signals after LSR section
old_block = '''        # ?????????
        try:
            lsr = fetch_long_short_ratio(sym)
            if lsr > 2.5: score -= 6; reasons.append('??????')
            elif lsr < 0.5: score += 6; reasons.append('??????')
        except Exception:
            pass'''

new_block = '''        # ?????????
        try:
            lsr = fetch_long_short_ratio(sym)
            if lsr > 2.5: score -= 6; reasons.append('??????')
            elif lsr < 0.5: score += 6; reasons.append('??????')
        except Exception:
            pass

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
        except Exception: pass'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print('New leading signals: added')
else:
    print('WARN: LSR block not found')

# 3. Update version
content = content.replace('v10', 'v11')
content = content.replace('?????v8 ??', '?????v11 ??|???+1mCVD+??|')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('yaobi_v8.py: compiled OK (v11)')
