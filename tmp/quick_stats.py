import json
LOG="/home/ubuntu/scripts/agents/signal_log.json"
with open(LOG) as f:
    entries = json.load(f)
all_sigs = []
for e in entries:
    src = e.get("source","?")
    for s in e["signals"]:
        all_sigs.append((src, s["sym"], s["dir"], s["price"]))

SOURCES = ["ambush","yaobi","mercu","reversal","surge"]
total = {}
for src, sym, direction, price in all_sigs:
    total[src] = total.get(src, 0) + 1

print("=== Signal counts ===")
for s in SOURCES:
    t = total.get(s, 0)
    print("  %s: %d" % (s, t))

# Latest reversal signals
rev_sigs = [(e["signals"][0]["sym"], e["signals"][0]["dir"], e["signals"][0].get("score",0)) 
            for e in entries if e["source"] == "reversal"]
print("\nReversal signals:", rev_sigs[-5:] if rev_sigs else "none")