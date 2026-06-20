import json, time
# Check both systems
d = json.load(open("/home/ubuntu/scripts/agents/hermes_state.json"))
ps = d.get("positions", {})

dy = json.load(open("/home/ubuntu/scripts/yaobi_state.json"))
yps = dy.get("positions", {})

print("=== ????? (orch) ===")
if ps:
    for k, v in ps.items():
        d_cn = "?" if v.get("direction")=="long" else "?"
        print(f"  {d_cn} {k}: @{v.get('entry_price')} PnL:{v.get('pnl_pct',0):+.1f}%")
else:
    print("  ??")

print(f"\n=== ???? (yb7) ===")
if yps:
    for k, v in list(yps.items())[:10]:
        print(f"  {v.get('direction')} {k}: @{v.get('entry')}")
else:
    print("  ??")

# Check latest orch signals
import subprocess
r = subprocess.run(["tail", "-30", "/tmp/orch.log"], capture_output=True, text=True)
for line in r.stdout.split("\n"):
    if "SIGNAL" in line and "BTC???" not in line:
        print(f"  [orch] {line.strip()[-80:]}")

r2 = subprocess.run(["tail", "-10", "/tmp/yb7.log"], capture_output=True, text=True)
for line in r2.stdout.split("\n"):
    if "??:" in line or "??:" in line:
        print(f"  [yb7] {line.strip()}")
