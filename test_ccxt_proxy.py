import os
os.environ["HTTP_PROXY"] = "http://172.18.0.1:7892"
os.environ["HTTPS_PROXY"] = "http://172.18.0.1:7892"

import ccxt
# Test Bybit
b = ccxt.bybit()
t = b.fetch_ticker("BTC/USDT")
print("CCXT Bybit BTC:", t["last"])

# Test Binance  
b2 = ccxt.binance()
t2 = b2.fetch_ticker("BTC/USDT")
print("CCXT Binance BTC:", t2["last"])

# Test ETH and SOL
t3 = b.fetch_ticker("ETH/USDT")
print("ETH:", t3["last"])
t4 = b.fetch_ticker("SOL/USDT")
print("SOL:", t4["last"])
