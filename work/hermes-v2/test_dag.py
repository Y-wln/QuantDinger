import sys, time, signal
sys.path.insert(0, '/home/ubuntu/hermes-v2')

class TOut(Exception): pass
def h(s, f): raise TOut()
signal.signal(signal.SIGALRM, h)

from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from indicators.scorer import Scorer
from services.dag import DAGConsensus

http = HTTPClient(2, 15)
ex = ExchangeAPI(http)
scorer = Scorer()
dag = DAGConsensus()

coins = ['DOGEUSDT', 'AVAXUSDT', 'SOLUSDT', 'ADAUSDT', 'BNBUSDT']
print(f"DAG Consensus Test {time.strftime('%H:%M:%S')}\n")

for sym in coins:
    try:
        signal.alarm(60)
        k4 = ex.klines(sym, '4h', 100)
        k1 = ex.klines(sym, '1h', 100)
        k5 = ex.klines(sym, '5m', 50)
        k15 = ex.klines(sym, '15m', 30)
        r = scorer.analyze(sym, k4, k1, k5, k15)
        signal.alarm(0)

        passed, reason, cs = dag.validate(r)
        d = r['direction'].upper()
        status = 'PASS' if passed else 'BLOCK'
        print(f"{status:6s} {sym:12s} Score:{r['score']:+4d} {d:6s} ${r['price']:.4f} DAG:{cs:+2d} | {reason}")
        if passed:
            for k, v in list(r['details'].items())[:5]:
                print(f"         {v}")
        print()
    except TOut:
        signal.alarm(0)
        print(f"  FAIL {sym}: TIMEOUT\n")
    except Exception as e:
        signal.alarm(0)
        print(f"  FAIL {sym}: {e}\n")
