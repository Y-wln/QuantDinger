import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')

# Read hermes_core.py
with open('/home/ubuntu/scripts/agents/hermes_core.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Rename the duplicate detect_launch to detect_launch_fast
content = content.replace('\ndef detect_launch(klines_5m):\n', '\ndef detect_launch_fast(klines_5m):\n')

# Verify we still have the 3-arg version
if 'def detect_launch(klines_5m, klines_15m, klines_1h):' not in content:
    print('ERROR: 3-arg detect_launch missing!')
    sys.exit(1)

# Check no more duplicate
count = content.count('def detect_launch(')
print(f'detect_launch occurrences after fix: {count}')

with open('/home/ubuntu/scripts/agents/hermes_core.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('hermes_core.py: fixed')

# Update entry_report.py
with open('/home/ubuntu/scripts/agents/entry_report.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('detect_launch, fetch_orderbook', 'detect_launch_fast, fetch_orderbook')
content = content.replace('ld, ls, lr = detect_launch(k5)', 'ld, ls, lr = detect_launch_fast(k5)')

with open('/home/ubuntu/scripts/agents/entry_report.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('entry_report.py: fixed')

# Verify imports work
import py_compile
py_compile.compile('/home/ubuntu/scripts/agents/hermes_core.py', doraise=True)
print('hermes_core.py: compiles OK')
py_compile.compile('/home/ubuntu/scripts/agents/entry_report.py', doraise=True)
print('entry_report.py: compiles OK')
