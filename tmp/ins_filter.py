with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    lines = f.readlines()

# Find the line numbers
long_insert_after = None
short_insert_after = None
for i, line in enumerate(lines):
    if "entry_warnings.append('RSI??" in line:
        long_insert_after = i
    if "entry_warnings.append('RSI??" in line:
        short_insert_after = i

if long_insert_after:
    indent = '            '
    block = [
        indent + "# check price position in 1h range\n",
        indent + "if len(k1) >= 20:\n",
        indent + "    h1_high = max(k['h'] for k in k1[-20:])\n",
        indent + "    h1_low = min(k['l'] for k in k1[-20:])\n",
        indent + "    if h1_high > h1_low:\n",
        indent + "        pos = (price - h1_low) / (h1_high - h1_low) * 100\n",
        indent + "        if pos > 70:\n",
        indent + "            entry_ok = False\n",
        indent + "            entry_warnings.append('1h high '+str(int(pos))+'% move done')\n",
    ]
    for j, bline in enumerate(block):
        lines.insert(long_insert_after + 1 + j, bline)
    print(f'Long filter inserted after line {long_insert_after+1}')

if short_insert_after:
    short_insert_after += len(block) if long_insert_after and long_insert_after < short_insert_after else 0
    indent = '            '
    block2 = [
        indent + "if len(k1) >= 20:\n",
        indent + "    h1_high = max(k['h'] for k in k1[-20:])\n",
        indent + "    h1_low = min(k['l'] for k in k1[-20:])\n",
        indent + "    if h1_high > h1_low:\n",
        indent + "        pos = (price - h1_low) / (h1_high - h1_low) * 100\n",
        indent + "        if pos < 30:\n",
        indent + "            entry_ok = False\n",
        indent + "            entry_warnings.append('1h low '+str(int(pos))+'% move done')\n",
    ]
    for j, bline in enumerate(block2):
        lines.insert(short_insert_after + 1 + j, bline)
    print(f'Short filter inserted after line {short_insert_after+1}')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.writelines(lines)

import os, py_compile
for f in os.listdir('/home/ubuntu/scripts/__pycache__'):
    if 'yaobi' in f:
        os.remove(os.path.join('/home/ubuntu/scripts/__pycache__', f))
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('Done')
