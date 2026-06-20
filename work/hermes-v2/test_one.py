import sys, time, traceback, signal
sys.path.insert(0, '/home/ubuntu/hermes-v2')

class TimeoutError(Exception): pass
def handler(s, f): raise TimeoutError("t/o")
signal.signal(signal.SIGALRM, handler)

from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from indicators.scorer import Scorer

http = HTTPClient(2, 15)
ex = ExchangeAPI(http)
scorer = Scorer()

sym = 'DOGEUSDT'
print(f"Testing {sym}...")
try:
    signal.alarm(20)
    k4 = ex.klines(sym, '4h', 100)
    signal.alarm(25)
    k1 = ex.klines(sym, '1h', 100)
    signal.alarm(25)
    k5 = ex.klines(sym, '5m', 50)
    signal.alarm(25)
    k15 = ex.klines(sym, '15m', 30)
    signal.alarm(30)
    r = scorer.analyze(sym, k4, k1, k5, k15)
    signal.alarm(0)
    d = r['direction'].upper()
    print(f"Score:{r['score']:+4d} {d} ${r['price']:.4f} {len(r['leading_signals'])} leading")
    for k, v in list(r['details'].items())[:10]:
        print(f"  {v}")
except TimeoutError:
    print("TIMEOUT")
except Exception as e:
    traceback.print_exc()
