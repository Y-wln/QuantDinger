import urllib.request, json
from datetime import datetime, timezone, timedelta

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
url = "https://fapi.binance.com/fapi/v1/klines?symbol=HUMAUSDT&interval=5m&limit=100"
data = json.loads(opener.open(url, timeout=15).read())
bjt = timezone(timedelta(hours=8))
for k in data[-40:]:
    t = datetime.fromtimestamp(k[0]/1000, tz=bjt).strftime("%m/%d %H:%M")
    o = float(k[1]); h = float(k[2]); l = float(k[3]); c = float(k[4]); v = float(k[5])
    chg = (c-o)/o*100
    print(f"{t} O:{o:.6f} H:{h:.6f} L:{l:.6f} C:{c:.6f} chg:{chg:+.2f}% V:{v:.0f}")
