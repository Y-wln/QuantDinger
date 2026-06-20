import json, time, os, sys
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import fetch_price

LOG = "/home/ubuntu/scripts/agents/signal_log.json"
SOURCES = ["ambush","yaobi","mercu","reversal","surge"]

while True:
    try:
        if not os.path.exists(LOG):
            time.sleep(30)
            continue
        with open(LOG) as f:
            entries = json.load(f)
        
        recent = entries[-100:]
        wins = {s: 0 for s in SOURCES}
        total = {s: 0 for s in SOURCES}
        
        for e in recent:
            src = e.get("source", "?")
            if src not in total:
                continue
            for s in e["signals"]:
                total[src] += 1
                sym = s["sym"] + "USDT"
                direction = s["dir"]
                entry_price = s["price"]
                
                try:
                    curr = fetch_price(sym)
                    if not curr or curr == 0:
                        continue
                    pnl = (curr - entry_price) / entry_price * 100 if direction == "long" else (entry_price - curr) / entry_price * 100
                    if pnl > 0:
                        wins[src] += 1
                except:
                    pass
        
        parts = []
        for src in SOURCES:
            t = total.get(src, 0)
            if t > 0:
                w = wins.get(src, 0)
                pct = str(round(w / t * 100)) + "%"
                parts.append("{}:{}({})".format(src[:4].title(), pct, t))
        
        line = "[{}] {}".format(time.strftime("%H:%M"), " | ".join(parts))
        print(line, flush=True)
        with open("/tmp/tracker.log", "a") as f:
            f.write(line + "\n")
        
        time.sleep(60)
    except Exception as ex:
        print("ERR:", ex, flush=True)
        time.sleep(30)