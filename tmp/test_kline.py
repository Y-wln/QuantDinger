import sys, os, time
sys.path.insert(0, "/home/ubuntu/hermes-v2")
os.chdir("/home/ubuntu/hermes-v2")
from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from core.klines import KlineCache
h = HTTPClient()
e = ExchangeAPI(h)
k = KlineCache(e)
t = time.time()
data = k.get("BTCUSDT", "4h", 300)
print(f"Got {len(data)} candles in {time.time()-t:.1f}s")
if data:
    print(f"First: {data[0]}")
    print(f"Last: {data[-1]}")
else:
    print("EMPTY - trying direct API call")
    t2 = time.time()
    raw = e.klines("BTCUSDT", "4h", 300)
    print(f"Direct API: {len(raw)} candles in {time.time()-t2:.1f}s")
