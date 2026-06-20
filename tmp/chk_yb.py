import json
print("=== ???? ===")
with open('/home/ubuntu/scripts/yaobi_state.json') as f:
    s = json.load(f)
pos = s.get('positions', {})
print(f"??: {len(pos)}")
print(f"??: {s.get('trades', 0)} | ??: {s.get('pnl', 0)}%")
for k, v in pos.items():
    print(f"  {k}: {v.get('direction')} @{v.get('entry')}")

print()
print("=== ???? ===")
import subprocess
r = subprocess.run(['tail', '-30', '/tmp/yb7.log'], capture_output=True, text=True)
for line in r.stdout.split('\n'):
    if any(w in line for w in ['??', '??', '??', 'RSI', '??']):
        print(line)
