import sys, py_compile, os
sys.path.insert(0, '/home/ubuntu/scripts/agents')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'r') as f:
    lines = f.readlines()

# Line 74: keep "        rs = rsi(c)"
# Line 75: delete the duplicate
# Line 76 onwards: keep
new_lines = []
for i, line in enumerate(lines):
    if i == 74:  # line 75 (0-indexed)
        continue  # skip duplicate
    new_lines.append(line)

# Verify
for i, line in enumerate(new_lines):
    if 'rs = rsi' in line:
        print(f'Line {i+1}: {line.rstrip()}')

with open('/home/ubuntu/scripts/yaobi_v8.py', 'w') as f:
    f.writelines(new_lines)

for f in os.listdir('/home/ubuntu/scripts/__pycache__'):
    if 'yaobi' in f:
        os.remove(os.path.join('/home/ubuntu/scripts/__pycache__', f))

py_compile.compile('/home/ubuntu/scripts/yaobi_v8.py', doraise=True)
print('yaobi_v8.py: RSI fix OK')
