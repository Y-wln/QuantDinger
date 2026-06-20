import json
with open("/home/ubuntu/scripts/agents/signal_log.json") as f:
    d = json.load(f)
for e in d[-3:]:
    for s in e["signals"]:
        print(e["time"], s["sym"], s["dir"], s["price"])
