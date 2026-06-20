import json, os

# 1. Kill orch first
os.system("screen -S orch -X quit 2>/dev/null")
os.system("sleep 1")

# 2. Force close ALL existing positions with current prices
state_file = "/home/ubuntu/scripts/agents/hermes_state.json"
with open(state_file) as f:
    d = json.load(f)

from hermes_core import fetch_price

positions = d.get("positions", {})
history = d.get("history", [])
stats = d.get("stats", {"total_trades": 0, "total_pnl": 0, "wins": 0})

for sym in list(positions.keys()):
    p = positions[sym]
    price = fetch_price(sym)
    if price <= 0:
        price = p["entry_price"]  # fallback
    direction = p["direction"]
    if direction == "long":
        pnl_pct = (price - p["entry_price"]) / p["entry_price"] * 100
    else:
        pnl_pct = (p["entry_price"] - price) / p["entry_price"] * 100
    
    p["exit_price"] = round(price, 4)
    p["exit_time"] = "force-clean"
    p["exit_reason"] = "????(v30.25)"
    p["pnl"] = round(pnl_pct, 2)
    p["pnl_pct"] = round(pnl_pct, 2)
    history.append(p)
    
    stats["total_trades"] = stats.get("total_trades", 0) + 1
    stats["total_pnl"] = round(stats.get("total_pnl", 0) + pnl_pct, 2)
    if pnl_pct > 0:
        stats["wins"] = stats.get("wins", 0) + 1
    
    print(f"CLOSED {sym} {direction}: PnL {pnl_pct:+.1f}%")

d["positions"] = {}
d["history"] = history
d["stats"] = stats

with open(state_file, "w") as f:
    json.dump(d, f, indent=2, default=str)

print(f"\n??: {stats['total_trades']}? | ?{stats['wins']} | PnL: {stats['total_pnl']:+.1f}%")

# 3. Restart orch
os.system("screen -dmS orch bash -c 'cd ~/scripts/agents && python3 -B -u agent_orchestrator.py >> /tmp/orch.log 2>&1'")
print("orch restarted")
