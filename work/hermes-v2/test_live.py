import sys, json, time
sys.path.insert(0, '/home/ubuntu/hermes-v2')
from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from indicators.scorer import Scorer

http = HTTPClient(retries=2, timeout=20)
ex = ExchangeAPI(http)
scorer = Scorer()

print("=== V2 Live Test ===")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print()

test_coins = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
for sym in test_coins:
    try:
        k4 = ex.klines(sym, '4h', 100)
        k1 = ex.klines(sym, '1h', 100)
        k5 = ex.klines(sym, '5m', 50)
        k15 = ex.klines(sym, '15m', 30)
        result = scorer.analyze(sym, k4, k1, k5, k15)
        d = result['direction'].upper()
        e = '🟢' if d == 'LONG' else ('🔴' if d == 'SHORT' else '🟡')
        print(f"{e} {sym:10s} Score:{result['score']:+4d}  Signal:{result['signal']:6s}  ${result['price']:.4f}")
        for k, v in list(result['details'].items())[:5]:
            print(f"   {v}")
        print()
    except Exception as e:
        print(f"X {sym}: {e}")
        print()

print("=== Done ===")
