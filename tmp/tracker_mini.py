import json, time, os
LOG = "/home/ubuntu/scripts/agents/signal_log.json"
while True:
    if os.path.exists(LOG):
        with open(LOG) as f:
            entries = json.load(f)
        total = {}
        for e in entries[-100:]:
            src = e.get("source","?")
            for s in e["signals"]:
                total[src] = total.get(src, 0) + 1
        line = "[{}] signals: {}".format(time.strftime("%H:%M"), total)
        print(line, flush=True)
        with open("/tmp/tracker.log", "a") as f:
            f.write(line + "\n")
    time.sleep(60)