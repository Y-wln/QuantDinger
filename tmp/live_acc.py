import json, sys, time
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import fetch_price

with open("/home/ubuntu/scripts/agents/signal_log.json") as f:
    entries = json.load(f)

# Group by source
results = {}
for e in entries:
    src = e.get("source", "?")
    if src not in results:
        results[src] = {"long": {"w":0,"l":0,"pnls":[]}, "short": {"w":0,"l":0,"pnls":[]}}
    
    for s in e["signals"]:
        direction = s["dir"]
        entry = s["price"]
        sym = s["sym"] + "USDT"
        score = s.get("score", 0)
        
        try:
            curr = fetch_price(sym)
            if not curr or curr == 0:
                continue
            pnl = (curr - entry) / entry * 100 if direction == "long" else (entry - curr) / entry * 100
            if pnl > 0:
                results[src][direction]["w"] += 1
            else:
                results[src][direction]["l"] += 1
            results[src][direction]["pnls"].append(pnl)
        except:
            pass

print("=" * 60)
print("  LIVE TRADING ACCURACY (current price vs entry)")
print("=" * 60)

for src in ["ambush","yaobi","reversal","mercu","surge","demon"]:
    if src not in results:
        continue
    r = results[src]
    print("\n--- %s ---" % src.upper())
    for d in ["long", "short"]:
        rd = r[d]
        total = rd["w"] + rd["l"]
        if total > 0:
            wr = rd["w"] / total * 100
            avg = sum(rd["pnls"]) / len(rd["pnls"])
            best = max(rd["pnls"])
            worst = min(rd["pnls"])
            print("  %s: %d/%d = %.0f%% | avg %+.2f%% | best %+.2f%% | worst %+.2f%%" % (
                d, rd["w"], rd["l"], wr, avg, best, worst))
    
    # Combined
    all_w = sum(r[d]["w"] for d in ["long","short"])
    all_l = sum(r[d]["l"] for d in ["long","short"])
    if all_w + all_l > 0:
        all_pnls = r["long"]["pnls"] + r["short"]["pnls"]
        print("  TOTAL: %d/%d = %.0f%% | avg %+.2f%%" % (
            all_w, all_l, all_w/(all_w+all_l)*100, 
            sum(all_pnls)/len(all_pnls) if all_pnls else 0))