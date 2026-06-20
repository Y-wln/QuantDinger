import json, time
time.sleep(20)
d = json.load(open("/home/ubuntu/scripts/agents/hermes_state.json"))
ps = d.get("positions", {})
if not ps:
    print("No positions")
for k, v in ps.items():
    print(f"{k}: pnl={v.get('pnl_pct','?')}% high={v.get('highest','?')} low={v.get('lowest','?')}")
print(f"Total positions: {len(ps)}")
print(f"Stats: {d.get('stats',{})}")
