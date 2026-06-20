import urllib.request, json
from datetime import datetime, timezone, timedelta

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
bjt = timezone(timedelta(hours=8))

signals = [
    ("HUSDT", 0.51946, "long", "15:18"),
    ("COAIUSDT", 0.5006, "short", "15:18"),
    ("HYPEUSDT", 60.412, "long", "15:23"),
    ("ZECUSDT", 426.89, "long", "15:24"),
    ("HUSDT", 0.51042, "long", "15:25"),
    ("SEIUSDT", 0.05336, "long", "15:26"),
]

for sym, entry, direction, stime in signals:
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + sym + "&interval=5m&limit=12"
    data = json.loads(opener.open(url, timeout=15).read())
    latest_c = float(data[-1][4])
    latest_t = datetime.fromtimestamp(data[-1][0]/1000, tz=bjt).strftime("%H:%M")
    if direction == "long":
        pnl = round((latest_c - entry)/entry*100, 2)
    else:
        pnl = round((entry - latest_c)/entry*100, 2)
    icon = "OK" if pnl > 0 else "XX"
    print(icon + " " + sym.replace("USDT","") + " " + direction + " @" + str(entry) + " (" + stime + ") -> now " + str(latest_c) + " (" + latest_t + ") PnL:" + str(pnl) + "%")
