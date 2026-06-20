import urllib.request, json
from datetime import datetime, timezone, timedelta

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)
bjt = timezone(timedelta(hours=8))

for sym, sig_price in [("COAIUSDT", 0.473), ("AEROUSDT", 0.3708), ("PLAYUSDT", 0.03333)]:
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + sym + "&interval=5m&limit=20"
    data = json.loads(opener.open(url, timeout=15).read())
    print("=== " + sym.replace("USDT","") + " (signal @" + str(sig_price) + ") ===")
    for k in data:
        t = datetime.fromtimestamp(k[0]/1000, tz=bjt).strftime("%H:%M")
        c = float(k[4]); v = float(k[5])
        o = float(k[1]); h = float(k[2]); l = float(k[3])
        chg = round((c-o)/o*100,2)
        pnl = round((c-sig_price)/sig_price*100, 2)
        print(t + " O:" + str(round(o,5)) + " H:" + str(round(h,5)) + " L:" + str(round(l,5)) + " C:" + str(round(c,5)) + " chg:" + str(chg) + "% V:" + str(int(v)) + " PnL:" + str(pnl) + "%")
    print()
