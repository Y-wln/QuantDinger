import sys, json
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import fetch_price as fp

positions = {
    'BNB': ('long', 597.23), 'BTC': ('long', 62105.99), 'DOGE': ('long', 0.0853),
    'XRP': ('long', 1.1413), 'ADA': ('long', 0.1683), 'LINK': ('long', 7.887),
    'DASH': ('short', 35.95), 'FET': ('long', 0.2038),
}

total = 0
for name, (d, entry) in positions.items():
    sym = name + 'USDT'
    price = fp(sym)
    if price:
        if d == 'long':
            pnl = (price - entry) / entry * 100
        else:
            pnl = (entry - price) / entry * 100
        total += pnl
        print(name, d, 'entry:', entry, 'now:', round(price,4), 'PnL:', round(pnl,2), '%')
    else:
        print(name, 'price fail')

print('Total floating PnL:', round(total, 2), '%')
