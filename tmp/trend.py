import json, urllib.request

proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

# Get 4h klines for trend check
coins = ["ESPORTSUSDT","ALLOUSDT","SYNUSDT","PORTALUSDT","INJUSDT","STGUSDT","IOUSDT","TRUMPUSDT","ENAUSDT","TAOUSDT"]
print("=== 4H TREND CHECK ===")
for sym in coins:
    try:
        url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + sym + "&interval=4h&limit=24"
        data = json.loads(opener.open(url, timeout=8).read())
        if not data: continue
        
        closes = [float(k[4]) for k in data]
        # Simple trend: price vs EMA20
        ema20 = sum(closes[-20:]) / min(len(closes), 20)
        current = closes[-1]
        ema_dev = (current - ema20) / ema20 * 100
        
        # 24h change
        chg24 = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0
        
        trend = "UP" if ema_dev > 0 else "DOWN"
        print("  %-12s price=%.4f  ema20=%.4f  dev=%+.1f%%  24h=%+.1f%%  [%s]" % (
            sym.replace("USDT",""), current, ema20, ema_dev, chg24, trend))
    except Exception as e:
        print("  %-12s ERR: %s" % (sym.replace("USDT",""), str(e)[:30]))