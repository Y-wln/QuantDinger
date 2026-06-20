import os

active = {
    "/home/ubuntu/hermes-v2/daemon.py": "daemon",
    "/home/ubuntu/hermes-v2/services/": "services",
    "/home/ubuntu/mercu-lab/run.py": "mercu-lab",
    "/home/ubuntu/scripts/agents/feishu_callback.py": "feishu",
    "/home/ubuntu/scripts/agents/liq_ws.py": "liqws",
    "/home/ubuntu/scripts/agents/selfcheck.py": "selfcheck",
}
yours = ["WyckoffTradingAgent","browser-use","TrendRadar","awesome-mcp-servers","freqtrade-technical","TradingAgents"]
deleted = ["hermes-workspace","hermes-ecosystem","openhanako","hermes-agent-orange-book","quantdinger","OpenHands","hummingbot_source","claude-task-master","CryptoTradingAgents"]
data_files = ["/home/ubuntu/hermes-v2/logs/v2_signals.jsonl","/home/ubuntu/hermes-v2/logs/v2_mercu.jsonl","/home/ubuntu/hermes-v2/logs/pipeline_tracker.json","/home/ubuntu/scripts/agents/mercu_data/anomaly-v4_limit_100.json"]

all_ok = True

print("=== Active projects ===")
for path, label in active.items():
    ok = os.path.exists(path)
    print("  " + ("OK" if ok else "MISSING") + " " + label)
    if not ok: all_ok = False

print("=== Your repos ===")
for d in yours:
    ok = os.path.exists("/home/ubuntu/" + d)
    print("  " + ("OK" if ok else "MISSING") + " " + d)
    if not ok: all_ok = False

print("=== Deleted (should be gone) ===")
for d in deleted:
    ok = os.path.exists("/home/ubuntu/" + d)
    print("  " + ("GONE" if not ok else "STILL EXISTS!") + " " + d)
    if ok: all_ok = False

print("=== Data files ===")
for path in data_files:
    ok = os.path.exists(path)
    print("  " + ("OK" if ok else "MISSING") + " " + os.path.basename(path))
    if not ok: all_ok = False

print("")
print("ALL OK" if all_ok else "ISSUES FOUND")
