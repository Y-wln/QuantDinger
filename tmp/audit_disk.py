
import os, subprocess

dirs_to_check = [
    "hermes-workspace", "hermes-ecosystem", "openhanako",
    "hermes-agent-orange-book", "WyckoffTradingAgent",
    "browser-use", "awesome-mcp-servers", "quantdinger",
    "OpenHands", "TrendRadar", "hummingbot_source",
    "claude-task-master", "freqtrade-technical", "CryptoTradingAgents",
    "TradingAgents"
]

active_dirs = ["hermes-v2", "mercu-lab", "scripts"]

print("=== SAFE TO DELETE (Git backed up) ===")
for d in dirs_to_check:
    path = os.path.join("/home/ubuntu", d)
    if not os.path.exists(path):
        continue
    size = subprocess.run(["du", "-sh", path], capture_output=True, text=True).stdout.strip().split("\t")[0]
    git_remote = ""
    if os.path.exists(os.path.join(path, ".git")):
        r = subprocess.run(["git", "-C", path, "remote", "-v"], capture_output=True, text=True)
        git_remote = r.stdout.split("\n")[0] if r.stdout.strip() else "no remote"
    print(f"  {d}: {size} | {git_remote}")

print()
print("=== ACTIVE (KEEP) ===")
for d in active_dirs:
    path = os.path.join("/home/ubuntu", d)
    if os.path.exists(path):
        size = subprocess.run(["du", "-sh", path], capture_output=True, text=True).stdout.strip().split("\t")[0]
        print(f"  {d}: {size} [ACTIVE - keep]")

print()
print("=== PYTHON CACHES ===")
for root, dirs, files in os.walk("/home/ubuntu"):
    if "__pycache__" in dirs:
        p = os.path.join(root, "__pycache__")
        s = sum(os.path.getsize(os.path.join(p, f)) for f in os.listdir(p) if os.path.isfile(os.path.join(p, f)))
        if s > 100000:
            print(f"  {p}: {s/1024/1024:.1f}MB")
    if root.count(os.sep) > 4:
        dirs.clear()

