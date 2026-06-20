import json
with open('/home/ubuntu/scripts/yaobi_state.json') as f:
    s = json.load(f)
pos = s.get('positions', {})
print(f"Yaobi????:")
print(f"  ??: {len(pos)}")
print(f"  ????: {s.get('trades', 0)}?")
print(f"  ????: {s.get('pnl', 0)}%")
for k, v in pos.items():
    print(f"  {k}: {v.get('direction')} @{v.get('entry')} sl={v.get('sl')} tp={v.get('tp')}")
