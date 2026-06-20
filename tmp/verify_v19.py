import urllib.request, json
proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

for sym, entry, direction in [("CHZUSDT", 0.02622, "long"), ("COAIUSDT", 0.4579, "short")]:
    url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym
    data = json.loads(opener.open(url, timeout=10).read())
    curr = float(data["price"])
    pnl = round((curr-entry)/entry*100,2) if direction=="long" else round((entry-curr)/entry*100,2)
    print(sym.replace("USDT","") + " " + direction + " @" + str(entry) + " now:" + str(curr) + " PnL:" + str(pnl) + "%")
