
import os

print("=" * 50)
print(" ŒÛ…æºÏ≤È")
print("=" * 50)

# Active projects - MUST exist
active = {
    "/home/ubuntu/hermes-v2/daemon.py": "hermes-v2 daemon",
    "/home/ubuntu/hermes-v2/services/": "hermes-v2 services",
    "/home/ubuntu/mercu-lab/run.py": "mercu-lab run",
    "/home/ubuntu/scripts/agents/feishu_callback.py": "feishu callback",
    "/home/ubuntu/scripts/agents/liq_ws.py": "liq ws",
    "/home/ubuntu/scripts/agents/selfcheck.py": "selfcheck",
}

print("\n[Active - MUST exist]")
all_ok = True
for path, label in active.items():
    if os.path.exists(path):
        print(f"  OK  {label}")
    else:
        print(f"  MISSING! {label} @ {path}")
        all_ok = False

# Your repos - MUST exist
yours = [
    "WyckoffTradingAgent", "browser-use", "TrendRadar",
    "awesome-mcp-servers", "freqtrade-technical", "TradingAgents"
]
print("\n[Your repos - MUST exist]")
for d in yours:
    path = os.path.join("/home/ubuntu", d)
    if os.path.exists(path):
        print(f"  OK  {d}")
    else:
        print(f"  MISSING! {d}")
        all_ok = False

# Deleted - MUST NOT exist
deleted = [
    "hermes-workspace", "hermes-ecosystem", "openhanako",
    "hermes-agent-orange-book", "quantdinger", "OpenHands",
    "hummingbot_source", "claude-task-master", "CryptoTradingAgents"
]
print("\n[Deleted - must NOT exist]")
for d in deleted:
    path = os.path.join("/home/ubuntu", d)
    if os.path.exists(path):
        print(f"  WARN {d} still exists!")
    else:
        print(f"  OK  {d} removed")

# Data files - MUST exist
data = [
    "/home/ubuntu/hermes-v2/logs/v2_signals.jsonl",
    "/home/ubuntu/hermes-v2/logs/v2_mercu.jsonl",
    "/home/ubuntu/hermes-v2/logs/pipeline_tracker.json",
    "/home/ubuntu/scripts/agents/mercu_data/anomaly-v4_limit_100.json",
]
print("\n[Data files - MUST exist]")
for path in data:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  OK  {os.path.basename(path)} ({size}B)")
    else:
        print(f"  MISSING! {path}")
        all_ok = False

# Self-check re-run
print("\n[Self-check quick]")
import subprocess
r = subprocess.run(["python3", "/home/ubuntu/scripts/agents/selfcheck.py"], 
                   capture_output=True, text=True, timeout=45)
fail_count = r.stdout.count("[FAIL]")
warn_count = r.stdout.count("[WARN]")
print(f"  Failures: {fail_count}, Warnings: {warn_count}")

print()
if all_ok:
    print("RESULT: No accidental deletions. All good.")
else:
    print("RESULT: ISSUES FOUND!")

