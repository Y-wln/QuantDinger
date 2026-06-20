import json, urllib.request

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

# Get all prices
resp = opener.open("https://fapi.binance.com/fapi/v1/ticker/price", timeout=15)
price_map = {p["symbol"]: float(p["price"]) for p in json.loads(resp.read())}

with open("/home/ubuntu/scripts/agents/signal_log.json") as f:
    entries = json.load(f)

# Collect ALL long signals with detailed features
longs = []
for e in entries:
    src = e.get("source","?")
    ts = e.get("ts", 0)
    for s in e["signals"]:
        if s["dir"] != "long":
            continue
        sym = s["sym"] + "USDT"
        curr = price_map.get(sym)
        if not curr: continue
        pnl = (curr - s["price"]) / s["price"] * 100
        score = s.get("score", 0)
        reasons = s.get("reasons", [])
        reason_str = "|".join(str(r)[:40] for r in reasons[:2])
        longs.append({
            "src": src, "pnl": pnl, "score": score, "win": pnl > 0,
            "sym": s["sym"], "age_min": (e["ts"] - ts) / 60 if ts else 0,
            "price": s["price"], "reasons": reason_str
        })

print("=" * 60)
print("LONG SIGNAL DEEP DIVE: %d signals" % len(longs))
print("=" * 60)

# 1. By source
print("\n--- By Strategy ---")
for src in ["ambush","mercu","reversal","yaobi","surge"]:
    subset = [l for l in longs if l["src"] == src]
    if not subset: continue
    w = sum(1 for l in subset if l["win"])
    avg = sum(l["pnl"] for l in subset) / len(subset)
    print("  %s: %d sigs, %.0f%% win, avg %+.2f%%" % (src, len(subset), w/len(subset)*100, avg))

# 2. By score bracket (ambush only)
print("\n--- Ambush LONG by Score ---")
ambush = [l for l in longs if l["src"] == "ambush"]
for thresh in [30, 40, 50, 60, 70]:
    sub = [l for l in ambush if l["score"] >= thresh]
    if sub:
        w = sum(1 for l in sub if l["win"])
        avg = sum(l["pnl"] for l in sub) / len(sub)
        print("  score>=%d: %d sigs, %.0f%% win, avg %+.2f%%" % (thresh, len(sub), w/len(sub)*100, avg))

# 3. Winners vs Losers analysis
winners = [l for l in ambush if l["win"]]
losers = [l for l in ambush if not l["win"]]
print("\n--- Winners vs Losers (Ambush) ---")
print("  Winners avg score: %.1f" % (sum(l["score"] for l in winners)/len(winners) if winners else 0))
print("  Losers avg score: %.1f" % (sum(l["score"] for l in losers)/len(losers) if losers else 0))
print("  Winners avg pnl: %+.2f%%" % (sum(l["pnl"] for l in winners)/len(winners) if winners else 0))
print("  Losers avg pnl: %+.2f%%" % (sum(l["pnl"] for l in losers)/len(losers) if losers else 0))

# 4. Top winning and losing coins
from collections import Counter
print("\n--- Best/Worst Coins (Ambush long) ---")
coin_stats = {}
for l in ambush:
    sym = l["sym"]
    if sym not in coin_stats:
        coin_stats[sym] = {"w":0,"l":0,"pnls":[]}
    if l["win"]: coin_stats[sym]["w"] += 1
    else: coin_stats[sym]["l"] += 1
    coin_stats[sym]["pnls"].append(l["pnl"])

for sym in sorted(coin_stats, key=lambda x: sum(coin_stats[x]["pnls"])/len(coin_stats[x]["pnls"]), reverse=True)[:8]:
    s = coin_stats[sym]
    t = s["w"]+s["l"]
    avg = sum(s["pnls"])/len(s["pnls"])
    print("  %s: %d sigs, %.0f%%, avg %+.2f%%" % (sym, t, s["w"]/t*100 if t else 0, avg))

# 5. Key insight: does score predict win?
print("\n--- Score vs Win Rate (Ambush long) ---")
for bracket in [(0,30),(30,40),(40,50),(50,60),(60,100)]:
    sub = [l for l in ambush if bracket[0] <= l["score"] < bracket[1]]
    if sub:
        w = sum(1 for l in sub if l["win"])
        avg = sum(l["pnl"] for l in sub) / len(sub)
        print("  score %d-%d: %d sigs, %.0f%% win, avg %+.2f%%" % (bracket[0], bracket[1], len(sub), w/len(sub)*100, avg))

# 6. Are newer signals better?
print("\n--- Signal Age vs Performance ---")
# approximate age from entry order
for i, fraction in enumerate([0.25, 0.5, 0.75, 1.0]):
    cut = int(len(ambush) * fraction)
    sub = ambush[-cut:] if cut > 0 else ambush
    if sub:
        w = sum(1 for l in sub if l["win"])
        avg = sum(l["pnl"] for l in sub) / len(sub)
        print("  newest %d%%: %d sigs, %.0f%% win, avg %+.2f%%" % (int(fraction*100), len(sub), w/len(sub)*100, avg))