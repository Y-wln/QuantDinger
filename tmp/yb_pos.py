import json
d = json.load(open("/home/ubuntu/scripts/yaobi_state.json"))
ps = d.get("positions", {})
print(f"????: {len(ps)}?")
for k, v in ps.items():
    print(f"  {k}: {v.get('direction')} @{v.get('entry')}")
print(f"??PnL: {d.get('pnl', 0)} ??: {d.get('trades', 0)}")
