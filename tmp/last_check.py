import json
d = json.load(open("/home/ubuntu/scripts/agents/hermes_state.json"))
ps = d.get("positions", {})
stats = d.get("stats", {})
print(f"??: {len(ps)} | ??: {stats.get('total_trades',0)} | PnL: {stats.get('total_pnl',0):+.1f}%")
for k, v in ps.items():
    print(f"  {v.get('direction')} {k}: @{v.get('entry_price')} PnL:{v.get('pnl_pct',0):+.1f}% ??:{v.get('entry_time','?')}")
