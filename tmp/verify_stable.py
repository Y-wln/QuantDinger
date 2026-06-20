import os, time, json, glob

# 1. Check service status
print("=== Service Status ===")
import subprocess
r = subprocess.run(["systemctl", "status", "mercu-poller", "--no-pager"], capture_output=True, text=True)
for line in r.stdout.split("\n")[:5]:
    print(line)

# 2. Check data freshness
data_dir = "/home/ubuntu/scripts/agents/mercu_data"
files = glob.glob(os.path.join(data_dir, "*.json"))
now = time.time()
print(f"\n=== Data Freshness (now={time.strftime('%H:%M:%S')}) ===")
for f in sorted(files):
    age = now - os.path.getmtime(f)
    if "anomaly" in f or "momentum" in f or "surge" in f or "rank" in f:
        flag = "FRESH" if age < 120 else "STALE" if age < 600 else "DEAD"
        print(f"  {os.path.basename(f):30s} {age:5.0f}s ago [{flag}]")

# 3. Check multiple data points over time (data rotation)
print("\n=== Data Update Pattern ===")
anomaly_file = os.path.join(data_dir, "anomaly-v4_100.json")
if os.path.exists(anomaly_file):
    with open(anomaly_file) as f:
        data = json.load(f)
    items = data.get("data", [])
    print(f"  anomaly-v4: {len(items)} items")
    if items:
        sample = items[0]
        print(f"  Latest event: {sample.get('sym','?')} {sample.get('main_dim','?')} {sample.get('l1_sentence','')[:80]}")

# 4. Verify V2 bridge
sys.path.insert(0, "/home/ubuntu/hermes-v2")
from services.mercu import MerCuBridge
m = MerCuBridge()
print(f"\n=== V2 Bridge ===")
print(f"  Data dir: {m.data_dir}")
print(f"  is_fresh(): {m.is_fresh()}")
signals = m.get_coin_signals()
print(f"  Signals: {len(signals)}")
for s in signals[:5]:
    print(f"    {s['direction']} {s['symbol']} score={s['score']} {s['reasons']}")
