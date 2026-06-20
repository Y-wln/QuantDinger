import json
from datetime import datetime

# Check hermes state
d = json.load(open("/home/ubuntu/scripts/agents/hermes_state.json"))
ps = d.get("positions", {})
stats = d.get("stats", {})
history = d.get("history", [])

print("=== ???? ===")
print(f"???: {stats.get('total_trades',0)}? | ?: {stats.get('wins',0)} | ??PnL: {stats.get('total_pnl',0):+.1f}%")

now = datetime.now()
longs = [v for v in ps.values() if v.get("direction")=="long"]
shorts = [v for v in ps.values() if v.get("direction")=="short"]
print(f"\n??: {len(longs)}? {len(shorts)}?")
print(f"????: {sum(v.get('pnl_pct',0) for v in longs):+.1f}%")
print(f"????: {sum(v.get('pnl_pct',0) for v in shorts):+.1f}%")

print("\n????:")
for k, v in ps.items():
    pnl = v.get("pnl_pct", 0)
    d_cn = "?" if v.get("direction")=="long" else "?"
    entry = v.get("entry_time", "?")
    try:
        et = datetime.strptime(entry, "%m-%d %H:%M")
        et = et.replace(year=now.year)
        hh = max(0, (now - et).total_seconds() / 3600)
    except: hh = -1
    flag = "??" if (hh > 8 and pnl < -1) else ("?" if hh > 24 else "  ")
    print(f"  {flag} {d_cn} {k}: @{v.get('entry_price')} PnL:{pnl:+.1f}% {hh:.0f}h ??:{entry}")

# Latest history
if history:
    print(f"\n??3???:")
    for h in history[-3:]:
        em = "??" if h.get("pnl_pct",0) > 0 else "??"
        print(f"  {em} {h.get('direction')} {h.get('exit_reason','?')}: {h.get('pnl_pct',0):+.1f}%")
