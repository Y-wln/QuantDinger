import sys, os
sys.path.insert(0, '/home/ubuntu/scripts/agents')
os.chdir('/home/ubuntu/scripts/agents')
from tracker_daemon import build_pipeline
p = build_pipeline()
sigs = p["signals"]
print("Pipeline signals:", len(sigs))
stages = {}
for v in sigs.values():
    for k in v:
        if k not in ("id", "symbol", "direction", "settled", "decision", "indicators"):
            stages[k] = stages.get(k, 0) + 1
print("Stages:", stages)
