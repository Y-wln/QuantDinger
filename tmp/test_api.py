import sys; sys.path.insert(0,"/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines, fetch_price
k = fetch_klines("BTCUSDT", "5m", 5)
print("BTC klines:", len(k) if k else "FAIL")
p = fetch_price("BTCUSDT")
print("BTC price:", p)
k2 = fetch_klines("IOUSDT", "5m", 5)
print("IO klines:", len(k2) if k2 else "FAIL")