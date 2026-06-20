import sys, time, traceback
sys.path.insert(0, '/home/ubuntu/hermes-v2')
from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from indicators.scorer import Scorer

http = HTTPClient(2, 20)
ex = ExchangeAPI(http)
scorer = Scorer()

coins = ['BTCUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SOLUSDT', 'FETUSDT', 'LINKUSDT']
print(f"=== V2 Enhanced Test {time.strftime('%H:%M:%S')} ===\n")
for sym in coins:
    try:
        k4 = ex.klines(sym, '4h', 100)
        k1 = ex.klines(sym, '1h', 100)
        k5 = ex.klines(sym, '5m', 50)
        k15 = ex.klines(sym, '15m', 30)
        r = scorer.analyze(sym, k4, k1, k5, k15)
        d = r['direction'].upper()
        e = 'LONG' if d == 'LONG' else ('SHORT' if d == 'SHORT' else 'WAIT')
        print(f"{'  ' + e:8s} {sym:12s} Score:{r['score']:+4d}  ${r['price']:.4f}  {len(r['leading_signals'])} leading")
        for k, v in list(r['details'].items())[:8]:
            print(f"         {v}")
        print()
    except Exception as e:
        print(f"  FAIL {sym}: {e}\n")
print('Done')
