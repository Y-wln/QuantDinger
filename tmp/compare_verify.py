import urllib.request, json

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

signals = [
    ("mercu", "TRUMPUSDT", 2.047, "short"),
    ("mercu", "BTCUSDT", 64390.0, "long"),
    ("mercu", "ETHUSDT", 1674.63, "long"),
    ("mercu", "ZECUSDT", 427.11, "long"),
    ("mercu", "TAOUSDT", 268.58, "short"),
    ("mercu", "BEATUSDT", 6.9638, "long"),
    ("mercu", "HUSDT", 0.53384, "long"),
    ("mercu", "COAIUSDT", 0.4639, "short"),
    ("mercu", "DOGEUSDT", 0.08707, "short"),
    ("yaobi", "TRUMPUSDT", 2.044, "short"),
]

mw = ml = yw = yl = 0
for source, sym, entry, direction in signals:
    url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym
    data = json.loads(opener.open(url, timeout=10).read())
    curr = float(data["price"])
    pnl = round((curr-entry)/entry*100,2) if direction=="long" else round((entry-curr)/entry*100,2)
    icon = "+" if pnl > 0 else "-"
    print(icon + " " + source.ljust(5) + " " + sym.replace("USDT","").ljust(6) + " " + direction.ljust(5) + " @" + str(entry).ljust(10) + " now:" + str(round(curr,5)).ljust(10) + " PnL:" + str(pnl) + "%")
    if source == "mercu":
        if pnl > 0: mw += 1
        else: ml += 1
    else:
        if pnl > 0: yw += 1
        else: yl += 1

print("")
print("MerCu: " + str(mw) + "/" + str(mw+ml) + " = " + str(round(mw/(mw+ml)*100)) + "%")
print("Yaobi: " + str(yw) + "/" + str(yw+yl) + " = " + str(round(yw/(yw+yl)*100)) + "%")
