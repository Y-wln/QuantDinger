import json, time, os
LOG = "/home/ubuntu/scripts/agents/signal_log.json"
SOURCES = ["ambush","yaobi","mercu","reversal","surge"]
while True:
    if os.path.exists(LOG):
        with open(LOG) as f:
            entries = json.load(f)
        recent = entries[-100:]
        total = {}
        for e in recent:
            src = e.get("source","?")
            for s in e["signals"]:
                total[src] = total.get(src, 0) + 1
        parts = []
        for s in SOURCES:
            t = total.get(s, 0)
            if t > 0:
                parts.append("{}:{}".format(s[:4].title(), t))
        line = "[{}] {}".format(time.strftime("%H:%M"), " | ".join(parts))
        print(line, flush=True)
        with open("/tmp/tracker.log", "a") as f:
            f.write(line + "\n")
    time.sleep(60)