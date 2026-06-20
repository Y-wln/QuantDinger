import json, os, subprocess

# 1. services
r = subprocess.run(["screen", "-ls"], capture_output=True, text=True)
print("=== SERVICES ===")
print(r.stdout)

# 2. positions
try:
    with open("/home/ubuntu/scripts/agents/hermes_state.json") as f:
        d = json.load(f)
    ps = d.get("positions", {})
    pnl = d.get("pnl", "N/A")
    print(f"PnL: {pnl}, Positions: {len(ps)}")
    for k,v in list(ps.items())[:12]:
        print(f"  {k}: dir={v.get('direction')} entry={v.get('entry_price')} pnl={v.get('pnl_pct','?')}")
except Exception as e:
    print(f"State error: {e}")

# 3. disk
print("=== DISK ===")
r2 = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
print(r2.stdout)

# 4. version
print("=== VERSION CHECK ===")
try:
    with open("/home/ubuntu/scripts/agents/agent_orchestrator.py") as f:
        for line in f:
            if "VERSION" in line and "=" in line:
                print(line.strip())
                break
except: pass
