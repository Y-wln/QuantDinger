import json, urllib.request

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

# Get BTC and market data
resp = opener.open("https://fapi.binance.com/fapi/v1/ticker/price", timeout=15)
price_map = {p["symbol"]: float(p["price"]) for p in json.loads(resp.read())}

# Check ESPORTS vs INJ vs BTC
for sym in ["ESPORTSUSDT","ALLOUSDT","SYNUSDT","PORTALUSDT","INJUSDT","STGUSDT","BTCUSDT"]:
    p = price_map.get(sym, 0)
    print("%s: %.6f" % (sym, p))

# Check 24h change for winners vs losers
print("\n24h changes:")
for sym in ["ESPORTSUSDT","ALLOUSDT","SYNUSDT","PORTALUSDT","INJUSDT","STGUSDT","BTCUSDT"]:
    try:
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=" + sym
        data = json.loads(opener.open(url, timeout=5).read())
        chg = float(data.get("priceChangePercent", 0))
        print("  %s: %+.2f%%" % (sym.replace("USDT",""), chg))
    except:
        print("  %s: ERR" % sym)