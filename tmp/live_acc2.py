import json, urllib.request, time

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

# Get all prices at once
print("Fetching prices...")
resp = opener.open("https://fapi.binance.com/fapi/v1/ticker/price", timeout=15)
all_prices = json.loads(resp.read())
price_map = {p["symbol"]: float(p["price"]) for p in all_prices}
print("Got %d prices" % len(price_map))

with open("/home/ubuntu/scripts/agents/signal_log.json") as f:
    entries = json.load(f)

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
        
        curr = price_map.get(sym)
        if not curr or curr == 0:
            continue
        
        pnl = (curr - entry) / entry * 100 if direction == "long" else (entry - curr) / entry * 100
        if pnl > 0:
            results[src][direction]["w"] += 1
        else:
            results[src][direction]["l"] += 1
        results[src][direction]["pnls"].append(pnl)

print("\n" + "=" * 60)
print("  LIVE TRADING ACCURACY")
print("=" * 60)

for src in ["ambush","yaobi","reversal","mercu","surge","demon"]:
    if src not in results: continue
    r = results[src]
    print("\n--- %s ---" % src.upper())
    for d in ["long", "short"]:
        rd = r[d]; t = rd["w"] + rd["l"]
        if t > 0:
            wr = rd["w"] / t * 100
            avg = sum(rd["pnls"]) / len(rd["pnls"])
            best = max(rd["pnls"]); worst = min(rd["pnls"])
            print("  %s: W%d L%d = %.0f%% | avg %+.2f%% | best %+.2f%% | worst %+.2f%%" % (d, rd["w"], rd["l"], wr, avg, best, worst))
    all_w = sum(r[d]["w"] for d in ["long","short"])
    all_l = sum(r[d]["l"] for d in ["long","short"])
    if all_w+all_l > 0:
        all_p = r["long"]["pnls"] + r["short"]["pnls"]
        print("  >> TOTAL: %.0f%% (%d/%d) avg %+.2f%%" % (all_w/(all_w+all_l)*100, all_w, all_w+all_l, sum(all_p)/len(all_p)))