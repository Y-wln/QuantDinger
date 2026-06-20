import json, urllib.request

with open("/home/ubuntu/scripts/agents/signal_log.json") as f:
    d = json.load(f)

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

# Get latest 10 ambush signals and verify
ambush_sigs = []
for e in d:
    if e.get("source") != "ambush": continue
    for s in e["signals"]:
        ambush_sigs.append((e["time"], s["sym"], s["dir"], s["price"]))

print(len(ambush_sigs), "ambush signals total")

# Verify last 12
wins = 0
for t, sym, direction, entry in ambush_sigs[-12:]:
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym + "USDT"
        curr = float(json.loads(opener.open(url, timeout=10).read())["price"])
        pnl = round((curr-entry)/entry*100,2) if direction=="long" else round((entry-curr)/entry*100,2)
        icon = "+" if pnl > 0 else "-"
        if pnl > 0: wins += 1
        print(icon + " " + t + " " + sym.ljust(8) + " " + direction.ljust(5) + " @" + str(entry).ljust(12) + " now:" + str(round(curr,6)).ljust(12) + " PnL:" + str(pnl) + "%")
    except Exception as e:
        print("ERR " + sym + ": " + str(e))

print("\nSample 12: " + str(wins) + "/12 = " + str(round(wins/12*100)) + "%")
