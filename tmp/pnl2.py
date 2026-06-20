import json, urllib.request
proxy = urllib.request.ProxyHandler({'http':'http://127.0.0.1:7892','https':'http://127.0.0.1:7892'})
opener = urllib.request.build_opener(proxy)

entries = {'BNBUSDT':('long',597.23),'BTCUSDT':('long',62105.99),'DOGEUSDT':('long',0.0853),'XRPUSDT':('long',1.1413),'ADAUSDT':('long',0.1683),'LINKUSDT':('long',7.887),'DASHUSDT':('short',35.95),'FETUSDT':('long',0.2038)}

total = 0
for sym, (dirn, entry) in entries.items():
    url = 'https://api.binance.com/api/v3/ticker/price?symbol=' + sym
    data = json.loads(opener.open(url, timeout=10).read())
    price = float(data['price'])
    pnl = (price-entry)/entry*100 if dirn=='long' else (entry-price)/entry*100
    total += pnl
    name = sym.replace('USDT','')
    print(name, dirn, 'entry=' + str(entry), 'now=' + str(round(price,4)), 'PnL=' + ('+' if pnl>0 else '') + str(round(pnl,2)) + '%')

print('Total floating PnL: ' + ('+' if total>0 else '') + str(round(total,2)) + '%')
