import urllib.request, json
from datetime import datetime, timezone, timedelta

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
url = "https://fapi.binance.com/fapi/v1/klines?symbol=HUMAUSDT&interval=5m&limit=40"
data = json.loads(opener.open(url, timeout=15).read())
bjt = timezone(timedelta(hours=8))
print(len(data), "klines")
for k in data[-20:]:
    t = datetime.fromtimestamp(k[0]/1000, tz=bjt).strftime("%m/%d %H:%M")
    print(t, round(float(k[4]), 6), int(float(k[5])))
