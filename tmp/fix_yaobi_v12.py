import sys, json
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'r', encoding='utf-8') as f:
    content = f.read()

changes = []

# 1. Max positions reduce from 8 to 5 (less is more for??)
old = 'MAX_POS = 8       # ????'
new = 'MAX_POS = 5       # ????(?????,???)'
if old in content:
    content = content.replace(old, new)
    changes.append('MAX_POS: 8->5')

# 2. SL wider for??: use 3x ATR instead of 2x
old_sl = "            positions[sym] = {'direction':'long','entry':s['price'],'sl':s['price']-atr_s*pat['sl_atr'],"
new_sl = "            positions[sym] = {'direction':'long','entry':s['price'],'sl':s['price']-atr_s*pat['sl_atr']*1.8,"
if old_sl in content:
    content = content.replace(old_sl, new_sl)
    changes.append('long SL: ATR*1.8')

old_sl2 = "            positions[sym] = {'direction':'short','entry':s['price'],'sl':s['price']+atr_s*pat['sl_atr'],"
new_sl2 = "            positions[sym] = {'direction':'short','entry':s['price'],'sl':s['price']+atr_s*pat['sl_atr']*1.8,"
if old_sl2 in content:
    content = content.replace(old_sl2, new_sl2)
    changes.append('short SL: ATR*1.8')

# 3. TP wider too
old_tp = "tp':s['price']+atr_s*pat['tp_atr']}"
new_tp = "tp':s['price']+atr_s*pat['tp_atr']*1.5}"
if old_tp in content:
    content = content.replace(old_tp, new_tp)
    changes.append('long TP: ATR*1.5')

old_tp2 = "tp':s['price']-atr_s*pat['tp_atr']}"
new_tp2 = "tp':s['price']-atr_s*pat['tp_atr']*1.5}"
if old_tp2 in content:
    content = content.replace(old_tp2, new_tp2)
    changes.append('short TP: ATR*1.5')

# 4. Raise signal threshold for?? (reduce false signals)
old_thresh = "    SIGNAL_THRESHOLD = 12"
new_thresh = "    SIGNAL_THRESHOLD = 18  # ??????,????"
if old_thresh in content:
    content = content.replace(old_thresh, new_thresh)
    changes.append('signal_threshold: 12->18')

# 5. Add entry confirmation: CVD must agree with direction
old_entry = """        if sc >= SIGNAL_THRESHOLD:
            # ??"""
new_entry = """        if sc >= SIGNAL_THRESHOLD:
            # CVD????(??????)
            cv_dir = 'long' if cv > 5 else ('short' if cv < -5 else 'neutral')
            if cv_dir != 'neutral' and cv_dir != d:
                continue  # CVD???????,??
            # ??"""
if old_entry in content:
    content = content.replace(old_entry, new_entry)
    changes.append('CVD direction confirmation')

content = content.replace('v11', 'v12')
content = content.replace('v10', 'v12')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('yaobi v12: compiled OK')
print('Changes:', changes)
