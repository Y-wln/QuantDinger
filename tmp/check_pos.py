import json
s = json.load(open('/home/ubuntu/scripts/agents/hermes_state.json'))
positions = s.get('positions', {})
print(f"Positions: {len(positions)}")
for k, v in positions.items():
    print(f"  {k}: {v.get('direction')} @{v.get('entry_price')} pnl={v.get('pnl_pct',0)}%")
