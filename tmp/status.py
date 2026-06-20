import json, os, time
from datetime import datetime, timezone, timedelta
BJT = timezone(timedelta(hours=8))

# Pipeline stats
d = json.load(open("/home/ubuntu/hermes-v2/logs/pipeline_tracker.json"))
pipes = d["pipelines"]
active = [p for p in pipes if p["status"] == "active"]
early = [p for p in pipes if p["status"] == "early"]
settled = [p for p in pipes if p.get("settled")]

# Find pipes with milestone snapshots
has_milestones = []
for p in pipes:
    ms = {k:v for k,v in p.items() if k.startswith("snap_") and k != "snapshots"}
    if ms:
        has_milestones.append((p["symbol"], ms))

print("=" * 50)
print("Pipeline Tracker Status")
print("=" * 50)
print(f"Total pipelines: {len(pipes)}")
print(f"Active (confirmed): {len(active)}")
print(f"Early (Âñ·üÖÐ): {len(early)}")
print(f"Settled (ÒÑ½áËã): {len(settled)}")
print()
print("Milestone snapshots found:", len(has_milestones))
for sym, ms in has_milestones[-5:]:
    print(f"  {sym}: {ms}")
print()

# Check cron log
cron_log = "/home/ubuntu/hermes-v2/logs/pipeline_cron.log"
if os.path.exists(cron_log):
    size = os.path.getsize(cron_log)
    mtime = datetime.fromtimestamp(os.path.getmtime(cron_log), BJT).strftime("%m/%d %H:%M")
    print(f"Cron log: {size} bytes, last modified {mtime}")

# Daemon uptime
import subprocess
r = subprocess.run(["ps", "-o", "etime=", "-p", "1478771"], capture_output=True, text=True)
uptime = r.stdout.strip()
print(f"Daemon uptime: {uptime}")

# File sizes
for f in ["v2_signals.jsonl", "v2_mercu.jsonl", "v2_yaobi.jsonl"]:
    path = f"/home/ubuntu/hermes-v2/logs/{f}"
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        mtime = datetime.fromtimestamp(os.path.getmtime(path), BJT).strftime("%H:%M")
        print(f"  {f}: {size_kb:.0f}KB (updated {mtime})")

