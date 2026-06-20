import urllib.request, json
from datetime import datetime, timezone, timedelta

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
bjt = timezone(timedelta(hours=8))

signals = [
    ("ALLOUSDT", 0.35409, "short"),
    ("HUSDT", 0.51946, "long"),
    ("COAIUSDT", 0.5006, "short"),
    ("HYPEUSDT", 60.412, "long"),
    ("ZECUSDT", 426.89, "long"),
    ("HUSDT", 0.51042, "long"),
    ("SEIUSDT", 0.05336, "long"),
    ("FETUSDT", 0.2126, "long"),
]

for sym, entry, direction in signals:
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + sym + "&interval=5m&limit=6"
    data = json.loads(opener.open(url, timeout=15).read())
    curr = float(data[-1][4])
    hi = max(float(k[2]) for k in data)
    lo = min(float(k[3]) for k in data)
    if direction == "long":
        pnl = round((curr - entry)/entry*100, 2)
    else:
        pnl = round((entry - curr)/entry*100, 2)
    icon = "+" if pnl > 0 else "-"
    print(icon + " " + sym.replace("USDT","").ljust(5) + " " + direction.ljust(5) + " @" + str(entry).ljust(10) + " curr:" + str(round(curr,5)).ljust(10) + " PnL:" + str(pnl) + "%")
