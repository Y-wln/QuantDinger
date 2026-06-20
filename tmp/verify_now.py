import urllib.request, json

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

signals = [
    ("mercu", "BTCUSDT", 64456.9, "long"),
    ("mercu", "ETHUSDT", 1676.83, "long"),
    ("mercu", "BEATUSDT", 6.7301, "short"),
    ("mercu", "ESPORTSUSDT", 0.0678, "short"),
    ("yaobi", "TAOUSDT", 273.82, "long"),
    ("yaobi", "ALLOUSDT", 0.36681, "long"),
    ("yaobi", "WLDUSDT", 0.5106, "long"),
    ("yaobi", "FETUSDT", 0.2131, "long"),
]

yw = yl = mw = ml = 0
for source, sym, entry, direction in signals:
    url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym
    data = json.loads(opener.open(url, timeout=10).read())
    curr = float(data["price"])
    pnl = round((curr-entry)/entry*100,2) if direction=="long" else round((entry-curr)/entry*100,2)
    icon = "+" if pnl > 0 else "-"
    print(icon + " " + source.ljust(5) + " " + sym.replace("USDT","").ljust(7) + " " + direction.ljust(5) + " @" + str(entry).ljust(10) + " now:" + str(round(curr,5)).ljust(10) + " PnL:" + str(pnl) + "%")
    if source == "mercu":
        if pnl > 0: mw += 1
        else: ml += 1
    else:
        if pnl > 0: yw += 1
        else: yl += 1

print("")
print("MerCu: " + str(mw) + "/" + str(mw+ml) + " = " + str(round(mw/(mw+ml)*100)) + "%")
print("Yaobi: " + str(yw) + "/" + str(yw+yl) + " = " + str(round(yw/(yw+yl)*100)) + "%")
