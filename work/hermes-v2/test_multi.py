import sys, time, traceback, signal
sys.path.insert(0, '/home/ubuntu/hermes-v2')

class TOut(Exception): pass
def h(s, f): raise TOut()
signal.signal(signal.SIGALRM, h)

from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from indicators.scorer import Scorer

http = HTTPClient(2, 15)
ex = ExchangeAPI(http)
scorer = Scorer()

for sym in ['DOGEUSDT', 'AVAXUSDT', 'SOLUSDT', 'LINKUSDT']:
    try:
        signal.alarm(90)
        k4 = ex.klines(sym, '4h', 100)
        k1 = ex.klines(sym, '1h', 100)
        k5 = ex.klines(sym, '5m', 50)
        k15 = ex.klines(sym, '15m', 30)
        r = scorer.analyze(sym, k4, k1, k5, k15)
        signal.alarm(0)
        d = r['direction'].upper()
        print(f"{sym:12s} Score:{r['score']:+4d} {d:6s} ${r['price']:.4f}")
        for k, v in list(r['details'].items())[:6]:
            print(f"  {v}")
        print()
    except TOut:
        signal.alarm(0)
        print(f"{sym:12s} TIMEOUT\n")
    except Exception as e:
        signal.alarm(0)
        print(f"{sym:12s} ERR: {e}\n")
