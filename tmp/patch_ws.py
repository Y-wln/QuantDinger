# -*- coding: utf-8 -*-
p = '/home/ubuntu/scripts/ws_sentinel.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

old = '            feishu_app_send'
new = '            print(f"[{t_str}] ALERT {cn} {dir_cn} {chg_pct:+.1f}%")\n            feishu_app_send'
code = code.replace(old, new)

old2 = '''    while True:
        t0 = time.time()
        scan()
        dt = time.time() - t0
        time.sleep(max(0.5, 2 - dt))'''

new2 = '''    scan_count = 0
    while True:
        t0 = time.time()
        scan()
        dt = time.time() - t0
        scan_count += 1
        if scan_count % 30 == 0:
            print(f'[{datetime.now(BJT).strftime("%H:%M:%S")}] heartbeat: {scan_count} scans')
        time.sleep(max(0.5, 2 - dt))'''

code = code.replace(old2, new2)

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)
print('patched')
