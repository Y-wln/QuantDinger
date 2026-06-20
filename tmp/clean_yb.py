import sys, os
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    lines = f.readlines()

# Fix lines 10-12: remove garbage remnants
new_lines = []
skip_next = 0
for i, line in enumerate(lines):
    if 'from entry_report import DEFAULT_PARAMS, COIN_PARAMS' in line:
        new_lines.append('from entry_report import DEFAULT_PARAMS, COIN_PARAMS\n')
        skip_next = 3  # skip the 3 garbage lines
        continue
    if skip_next > 0:
        skip_next -= 1
        continue
    new_lines.append(line)

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.writelines(new_lines)

# Clear cache
for f in os.listdir('/home/ubuntu/scripts/__pycache__'):
    if 'yaobi' in f:
        os.remove(os.path.join('/home/ubuntu/scripts/__pycache__', f))

import py_compile
py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('yaobi_v8.py v12: clean compile OK')
