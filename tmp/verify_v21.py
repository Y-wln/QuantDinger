import urllib.request, json
proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

signals = [
    ("yaobi", "MEGAUSDT", 0.06649, "long"),
    ("yaobi", "CHIPUSDT", 0.03624, "long"),
    ("yaobi", "KAITOUSDT", 0.472, "long"),
    ("mercu", "ESPORTSUSDT", 0.0678, "long"),
]

yw=yl=mw=ml=0
for source, sym, entry, direction in signals:
    url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=" + sym
    data = json.loads(opener.open(url, timeout=10).read())
    curr = float(data["price"])
    pnl = round((curr-entry)/entry*100,2) if direction=="long" else round((entry-curr)/entry*100,2)
    print(source + " " + sym.replace("USDT","").ljust(7) + " " + direction + " @" + str(entry) + " now:" + str(round(curr,5)) + " PnL:" + str(pnl) + "%")
    if source=="mercu":
        if pnl>0: mw+=1
        else: ml+=1
    else:
        if pnl>0: yw+=1
        else: yl+=1

print("Yaobi: " + str(yw) + "/" + str(yw+yl) + "=" + str(round(yw/max(yw+yl,1)*100)) + "%")
print("MerCu: " + str(mw) + "/" + str(mw+ml) + "=" + str(round(mw/max(mw+ml,1)*100)) + "%")
