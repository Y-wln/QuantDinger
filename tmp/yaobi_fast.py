import os, py_compile

with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    content = f.read()

changes = []

# 1. Scan interval 180->15 (was already changed to 60 earlier, now drop further)
content = content.replace('time.sleep(60)', 'time.sleep(10)')
changes.append('scan interval: 60->10s')

# 2. Add flash trigger: if any single leading indicator is extreme, fire immediately
# Find the signal determination line
old_sig = "sig = 'long' if score >= th else ('short' if score <= -th else 'wait')"
new_sig = """sig = 'long' if score >= th else ('short' if score <= -th else 'wait')
        # Flash trigger: single extreme indicator = immediate signal
        if sig == 'wait':
            flash_score = 0
            flash_reasons = []
            # 1m CVD > 40% = flash
            try:
                cvd1m_val = fetch_1m_cvd(sym)
                if cvd1m_val > 40:
                    flash_score = 8; flash_reasons.append('1m??'+str(int(cvd1m_val))+'%')
                    sig = 'long'
                elif cvd1m_val < -40:
                    flash_score = -8; flash_reasons.append('1m??'+str(int(cvd1m_val))+'%')
                    sig = 'short'
            except: pass
            # Orderbook > 25% = flash
            if sig == 'wait':
                try:
                    ob_val = fetch_orderbook_imbalance(sym)
                    if ob_val and ob_val.get('imbalance', 0) > 25:
                        flash_score = 8; flash_reasons.append('???????'+str(ob_val['imbalance'])+'%')
                        sig = 'long'
                    elif ob_val and ob_val.get('imbalance', 0) < -25:
                        flash_score = -8; flash_reasons.append('???????'+str(ob_val['imbalance'])+'%')
                        sig = 'short'
                except: pass
            # 5m vol > 4x = flash
            if sig == 'wait':
                try:
                    if vr > 4.0:
                        flash_score = 8 if k5[-1]['c'] > k5[-1]['o'] else -8
                        flash_reasons.append('5m??'+str(round(vr,1))+'x')
                        sig = 'long' if flash_score > 0 else 'short'
                except: pass
            if flash_score != 0:
                score = flash_score * 3
                reasons = flash_reasons
                entry_ok = True
                entry_warnings = []"""

content = content.replace(old_sig, new_sig)
changes.append('flash trigger: added')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.write(content)

for d in ['/home/ubuntu/scripts/__pycache__', '/home/ubuntu/scripts/agents/__pycache__']:
    if os.path.exists(d):
        for f in os.listdir(d):
            if 'yaobi' in f:
                os.remove(os.path.join(d, f))

py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('Done:', changes)
