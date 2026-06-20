import urllib.request, json
from datetime import datetime, timezone, timedelta

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
bjt = timezone(timedelta(hours=8))

for sym in ["AEROUSDT", "PLAYUSDT"]:
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + sym + "&interval=5m&limit=30"
    data = json.loads(opener.open(url, timeout=15).read())
    print("=== " + sym + " ===")
    for k in data[-15:]:
        t = datetime.fromtimestamp(k[0]/1000, tz=bjt).strftime("%H:%M")
        o = float(k[1]); c = float(k[4]); v = float(k[5])
        chg = (c-o)/o*100
        print(t + " O:" + str(round(o,6)) + " C:" + str(round(c,6)) + " chg:" + str(round(chg,2)) + "% V:" + str(int(v)))
    print()
