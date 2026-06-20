import urllib.request, json

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

signals = [("WLDUSDT", 0.5026, "short"), ("TAOUSDT", 268.82, "short")]
for sym, entry, direction in signals:
    url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym
    data = json.loads(opener.open(url, timeout=10).read())
    curr = float(data["price"])
    pnl = round((entry-curr)/entry*100, 2)
    print(sym.replace("USDT","") + " short @" + str(entry) + " now:" + str(curr) + " PnL:" + str(pnl) + "%")
