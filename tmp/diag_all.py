import sys, json
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import fetch_klines, fetch_price, fetch_fear_greed
from agent_technical import TechnicalAgent

ta = TechnicalAgent()
fng = fetch_fear_greed()
coins = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','DOGEUSDT','LINKUSDT','AVAXUSDT']

for sym in coins:
    k4 = fetch_klines(sym, '4h', 300)
    k1 = fetch_klines(sym, '1h', 300)
    k5 = fetch_klines(sym, '5m', 50)
    k15 = fetch_klines(sym, '15m', 30)
    if len(k4) < 50 or len(k1) < 50:
        print(f"{sym}: insufficient data")
        continue
    r = ta.analyze(k4, k1, k5, k15, sym, fng=fng)
    price = fetch_price(sym)
    print(f"{sym.replace('USDT',''):6s} ${price:<10.4f} score={r['score']:4d} signal={r['signal']:6s}")
