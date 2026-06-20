import urllib.request, json
from datetime import datetime, timezone, timedelta

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
url = "https://fapi.binance.com/fapi/v1/klines?symbol=HUMAUSDT&interval=5m&limit=60"
data = json.loads(opener.open(url, timeout=15).read())
bjt = timezone(timedelta(hours=8))
print(len(data), "klines total")
for k in data:
    t = datetime.fromtimestamp(k[0]/1000, tz=bjt).strftime("%m/%d %H:%M")
    o = float(k[1]); c = float(k[4]); v = float(k[5])
    chg = (c-o)/o*100
    print(f"{t} O:{o:.6f} C:{c:.6f} chg:{chg:+.2f}% V:{v:.0f}")
