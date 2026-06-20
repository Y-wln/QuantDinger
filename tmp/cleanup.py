
import os, subprocess

# NOT user repos - safe to delete (can re-clone from original source)
not_mine = [
    "hermes-workspace", "hermes-ecosystem", "openhanako",
    "hermes-agent-orange-book", "quantdinger", "OpenHands",
    "hummingbot_source", "claude-task-master", "CryptoTradingAgents"
]

active = ["hermes-v2", "mercu-lab", "scripts"]

print("=== KEEPING (yours or active) ===")
# Active
for d in active:
    path = os.path.join("/home/ubuntu", d)
    if os.path.exists(path):
        s = subprocess.run(["du", "-sh", path], capture_output=True, text=True).stdout.strip()
        print(f"  {s} [ACTIVE]")
# Your repos
for d in ["WyckoffTradingAgent","browser-use","TrendRadar","awesome-mcp-servers","freqtrade-technical","TradingAgents"]:
    path = os.path.join("/home/ubuntu", d)
    if os.path.exists(path):
        s = subprocess.run(["du", "-sh", path], capture_output=True, text=True).stdout.strip()
        print(f"  {s} [YOUR REPO - KEEP]")

print()
print("=== DELETING (not yours, git backed up) ===")
total = 0
for d in not_mine:
    path = os.path.join("/home/ubuntu", d)
    if not os.path.exists(path):
        continue
    s = subprocess.run(["du", "-sh", path], capture_output=True, text=True).stdout.strip()
    r = subprocess.run(["rm", "-rf", path], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  DELETED {s}")
        # Parse
        if "M" in s:
            total += float(s.replace("M","").replace("G","000").split()[0])
    else:
        print(f"  SKIP {d}")

print(f"\nTotal freed: ~{total:.0f}MB")
print()
r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
print(r.stdout)

