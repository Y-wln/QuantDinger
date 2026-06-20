import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/agents/agent_orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import for new leading signals
old_import = 'from hermes_core import (feishu_send, load_state, save_state, should_alert,'
new_import = '''from hermes_core import (feishu_send, load_state, save_state, should_alert,
    fetch_orderbook_imbalance, fetch_1m_cvd, fetch_tape_pressure,'''
content = content.replace(old_import, new_import)
print('Import: updated')

# Add 3 new leading signals before the return in leading_confirm
# Find the line "sig['fng'] = fng" and add after it
old_block = """        sig['fng'] = fng
        except Exception:
            pass

        sig['leading_bonus'] = bonus
        sig['leading_reasons'] = reasons
        return sig"""

new_block = """        sig['fng'] = fng
        except Exception:
            pass

        # === 6. ?????? ===
        try:
            ob = fetch_orderbook_imbalance(sym)
            if ob:
                imb = ob.get('imbalance', 0)
                sig['orderbook'] = imb
                if direction == 'long' and imb > 10:
                    bonus += 10; reasons.append('?????+10')
                elif direction == 'short' and imb < -10:
                    bonus += 10; reasons.append('?????+10')
                elif (direction == 'long' and imb < -10) or (direction == 'short' and imb > 10):
                    bonus -= 5; reasons.append('???????-5')
        except Exception:
            pass

        # === 7. 1m??CVD ===
        try:
            cvd1m = fetch_1m_cvd(sym)
            sig['cvd1m'] = cvd1m
            if direction == 'long' and cvd1m > 20:
                bonus += 12; reasons.append('1mCVD??+12')
            elif direction == 'short' and cvd1m < -20:
                bonus += 12; reasons.append('1mCVD??+12')
            elif direction == 'long' and cvd1m > 8:
                bonus += 6; reasons.append('1mCVD??+6')
            elif direction == 'short' and cvd1m < -8:
                bonus += 6; reasons.append('1mCVD??+6')
            elif (direction == 'long' and cvd1m < -8) or (direction == 'short' and cvd1m > 8):
                bonus -= 8; reasons.append('1mCVD????-8')
        except Exception:
            pass

        # === 8. ????? ===
        try:
            tape = fetch_tape_pressure(sym)
            if tape:
                sig['tape'] = tape.get('pressure', 'neutral')
                lp = tape.get('large_net', 0)
                if direction == 'long' and tape['pressure'] == 'bullish':
                    bonus += 8; reasons.append('?????+8')
                elif direction == 'short' and tape['pressure'] == 'bearish':
                    bonus += 8; reasons.append('?????+8')
                if abs(lp) >= 3 and ((direction == 'long' and lp > 0) or (direction == 'short' and lp < 0)):
                    bonus += 6; reasons.append('????+6')
        except Exception:
            pass

        sig['leading_bonus'] = bonus
        sig['leading_reasons'] = reasons
        return sig"""

content = content.replace(old_block, new_block)
print('leading_confirm: 3 new signals added')

with open('/home/ubuntu/scripts/agents/agent_orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/agent_orchestrator.py', doraise=True)
print('agent_orchestrator.py: compiles OK')
