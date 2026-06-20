import sys, json, urllib.request, socket
sys.path.insert(0,"/home/ubuntu/scripts/agents")
proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})

socket.setdefaulttimeout(8)

coins = ["IOUSDT","ENAUSDT","TAOUSDT","FETUSDT","WLDUSDT","ONDOUSDT","STGUSDT","PLAYUSDT","COAIUSDT","MEGAUSDT"]
for sym in coins:
    try:
        opener = urllib.request.build_opener(proxy)
        url = "https://fapi.binance.com/fapi/v1/klines?symbol=%s&interval=5m&limit=20" % sym
        resp = opener.open(url, timeout=5)
        data = json.loads(resp.read())
        if data:
            vols = [float(k[5]) for k in data]
            avg_v = sum(vols[:-3]) / max(len(vols)-3, 1)
            last_v = vols[-2]
            last_o = float(data[-2][1]); last_c = float(data[-2][4])
            last_chg = (last_c - last_o) / last_o * 100 if last_o > 0 else 0
            curr_o = float(data[-1][1]); curr_c = float(data[-1][4])
            curr_chg = (curr_c - curr_o) / curr_o * 100 if curr_o > 0 else 0
            vr = last_v / max(avg_v, 0.001)
            print("%s: vr=%.1fx chg_p=%.2f%% chg_c=%.2f%%" % (sym, vr, last_chg, curr_chg))
        else:
            print("%s: no data" % sym)
    except Exception as e:
        print("%s: ERR - %s" % (sym, str(e)[:50]))