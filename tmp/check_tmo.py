import json
d = json.load(open("/home/ubuntu/scripts/agents/hermes_state.json"))
ps = d.get("positions", {})
from datetime import datetime
now = datetime.now()
for k, v in ps.items():
    pnl = v.get("pnl_pct", 0)
    entry = v.get("entry_time", "?")
    try:
        et = datetime.strptime(entry, "%m-%d %H:%M")
        et = et.replace(year=now.year)
        hours = (now - et).total_seconds() / 3600
        if hours < 0: hours += 365*24
    except: hours = -1
    emoji = "??" if (hours > 8 and pnl < -1) or (hours > 24 and pnl < 0.5) else "  "
    print(f"{emoji}{k}: {v.get('direction')} PnL:{pnl:+.1f}% {hours:.0f}h ??:{entry}")
