import json, urllib.request
url = 'https://api.binance.com/api/v3/ticker/price?symbols=[%22BNBUSDT%22,%22BTCUSDT%22,%22DOGEUSDT%22,%22XRPUSDT%22,%22ADAUSDT%22,%22LINKUSDT%22,%22DASHUSDT%22,%22FETUSDT%22]'
data = json.loads(urllib.request.urlopen(url, timeout=10).read())
entries = {'BNBUSDT':('long',597.23),'BTCUSDT':('long',62105.99),'DOGEUSDT':('long',0.0853),'XRPUSDT':('long',1.1413),'ADAUSDT':('long',0.1683),'LINKUSDT':('long',7.887),'DASHUSDT':('short',35.95),'FETUSDT':('long',0.2038)}
total = 0
for d in data:
    sym = d['symbol']; price = float(d['price'])
    dirn, entry = entries.get(sym, (None,0))
    if dirn:
        pnl = (price-entry)/entry*100 if dirn=='long' else (entry-price)/entry*100
        total += pnl
        print(sym.replace('USDT',''), dirn, 'entry:', entry, 'now:', round(price,4), 'PnL:', round(pnl,2), '%')
print('Total floating PnL:', round(total, 2), '%')
