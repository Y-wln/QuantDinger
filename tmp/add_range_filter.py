import os, py_compile

with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    content = f.read()

# Add range position check for LONG signals
old_long = """            if rs > 70:
                entry_ok = False
                entry_warnings.append('RSI??'+str(int(rs))+'????')
        elif sig == 'short':"""

new_long = """            if rs > 70:
                entry_ok = False
                entry_warnings.append('RSI??'+str(int(rs))+'????')
            # 1h range check: dont chase if price already in top 30%
            if len(k1) >= 20:
                h1_high = max(k['h'] for k in k1[-20:])
                h1_low = min(k['l'] for k in k1[-20:])
                if h1_high > h1_low:
                    pos = (price - h1_low) / (h1_high - h1_low) * 100
                    if pos > 70:
                        entry_ok = False
                        entry_warnings.append('1h??'+str(int(pos))+'% ?????')
        elif sig == 'short':"""

if old_long in content:
    content = content.replace(old_long, new_long)
    print('Long range filter: added')
else:
    print('Long block not found!')

# Add range position check for SHORT signals
old_short = """            if rs < 30:
                entry_ok = False
                entry_warnings.append('RSI??'+str(int(rs))+'????')
        return {'sym': sym,"""

new_short = """            if rs < 30:
                entry_ok = False
                entry_warnings.append('RSI??'+str(int(rs))+'????')
            if len(k1) >= 20:
                h1_high = max(k['h'] for k in k1[-20:])
                h1_low = min(k['l'] for k in k1[-20:])
                if h1_high > h1_low:
                    pos = (price - h1_low) / (h1_high - h1_low) * 100
                    if pos < 30:
                        entry_ok = False
                        entry_warnings.append('1h??'+str(int(pos))+'% ?????')
        return {'sym': sym,"""

if old_short in content:
    content = content.replace(old_short, new_short)
    print('Short range filter: added')
else:
    print('Short block not found!')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.write(content)

for f in os.listdir('/home/ubuntu/scripts/__pycache__'):
    if 'yaobi' in f:
        os.remove(os.path.join('/home/ubuntu/scripts/__pycache__', f))

py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('Compiled OK')
