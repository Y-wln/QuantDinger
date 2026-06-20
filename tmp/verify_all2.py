import urllib.request, json

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

signals = [
    ("ALLOUSDT", 0.35409, "short"), ("HUSDT", 0.51946, "long"),
    ("COAIUSDT", 0.5006, "short"), ("HYPEUSDT", 60.412, "long"),
    ("ZECUSDT", 426.89, "long"), ("HUSDT", 0.51042, "long"),
    ("SEIUSDT", 0.05336, "long"), ("FETUSDT", 0.2126, "long"),
    ("TRADOORUSDT", 0.5467, "long"),
]

wins = 0
for sym, entry, direction in signals:
    url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym
    data = json.loads(opener.open(url, timeout=10).read())
    curr = float(data["price"])
    pnl = round((curr-entry)/entry*100, 2) if direction=="long" else round((entry-curr)/entry*100, 2)
    icon = "+" if pnl > 0 else "-"
    if pnl > 0: wins += 1
    print(icon + " " + sym.replace("USDT","").ljust(7) + " " + direction.ljust(5) + " @" + str(entry).ljust(10) + " now:" + str(round(curr,5)).ljust(10) + " PnL:" + str(pnl) + "%")

print("")
print(str(wins) + "/" + str(len(signals)) + " = " + str(round(wins/len(signals)*100)) + "%")
