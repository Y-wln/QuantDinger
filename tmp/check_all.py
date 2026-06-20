import json

# Yaobi state
with open('/home/ubuntu/scripts/yaobi_state.json') as f:
    yb = json.load(f)
print("=== ?????(????) ===")
print(f"  ??: {len(yb.get('positions',{}))}/8")
print(f"  ????: {yb.get('trades',0)}?")
print(f"  ????: {yb.get('pnl',0):+.1f}%")

# Paper trader state
try:
    with open('/home/ubuntu/trading_logs/yaobi_paper/state.json') as f:
        pp = json.load(f)
    stats = pp.get('stats',{})
    print(f"\n=== ????(12???) ===")
    print(f"  ??: {len(pp.get('positions',{}))}/8")
    print(f"  ????: {stats.get('trades',0)}?")
    print(f"  ??: {round(stats.get('wins',0)/max(1,stats.get('trades',1))*100,1)}%")
    print(f"  ????: {stats.get('total_pnl',0):+.1f}%")
except:
    print("\n=== ???? ===")
    print("  (???)")

# Orch state
with open('/home/ubuntu/scripts/agents/hermes_state.json') as f:
    orch = json.load(f)
pos = orch.get('positions',{})
total_pnl = sum(v.get('pnl_pct',0) for v in pos.values())
print(f"\n=== Hermes???(????) ===")
print(f"  ??: {len(pos)}/8")
print(f"  ????: {total_pnl:+.1f}%")
