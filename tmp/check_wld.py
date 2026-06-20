import urllib.request, json
from datetime import datetime, timezone, timedelta

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
bjt = timezone(timedelta(hours=8))

# WLD 1m klines for detailed view
for interval, limit in [("1m", 60), ("5m", 30)]:
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=WLDUSDT&interval=" + interval + "&limit=" + str(limit)
    data = json.loads(opener.open(url, timeout=15).read())
    print("=== WLD " + interval + " (" + str(len(data)) + " klines) ===")
    for k in data:
        t = datetime.fromtimestamp(k[0]/1000, tz=bjt).strftime("%H:%M")
        o = float(k[1]); h = float(k[2]); l = float(k[3]); c = float(k[4]); v = float(k[5])
        chg = round((c-o)/o*100, 2)
        print(t + " O:" + str(round(o,4)) + " H:" + str(round(h,4)) + " L:" + str(round(l,4)) + " C:" + str(round(c,4)) + " chg:" + str(chg) + "% V:" + str(int(v)))
    print()
