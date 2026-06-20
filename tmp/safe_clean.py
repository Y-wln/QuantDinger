
import os, subprocess

safe_dirs = [
    "hermes-workspace", "hermes-ecosystem", "openhanako",
    "hermes-agent-orange-book", "WyckoffTradingAgent",
    "browser-use", "awesome-mcp-servers", "quantdinger",
    "OpenHands", "TrendRadar", "hummingbot_source",
    "claude-task-master", "freqtrade-technical", "CryptoTradingAgents",
    "TradingAgents"
]

print("=== Checking for uncommitted changes ===")
clean = []
dirty = []
for d in safe_dirs:
    path = os.path.join("/home/ubuntu", d)
    if not os.path.exists(path):
        continue
    r = subprocess.run(["git", "-C", path, "status", "--short"], capture_output=True, text=True)
    size = subprocess.run(["du", "-sh", path], capture_output=True, text=True).stdout.strip().split("\t")[0]
    if r.stdout.strip():
        dirty.append((d, size, r.stdout.strip()[:100]))
    else:
        clean.append((d, size))

total_clean = 0
print("\nSAFE TO DELETE (clean git, can re-clone):")
for d, size in clean:
    print(f"  {d}: {size}")
    # Parse size
    if "M" in size:
        total_clean += float(size.replace("M",""))
    
print(f"\n  Total: ~{total_clean:.0f}MB")

if dirty:
    print("\nSKIP (has uncommitted changes):")
    for d, size, changes in dirty:
        print(f"  {d}: {size} - {changes}")

# Actually delete
print("\n=== DELETING ===")
for d, size in clean:
    path = os.path.join("/home/ubuntu", d)
    r = subprocess.run(["rm", "-rf", path], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  DELETED {d}: {size}")
    else:
        print(f"  FAILED {d}: {r.stderr}")

print("\n=== RESULT ===")
r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
print(r.stdout)

