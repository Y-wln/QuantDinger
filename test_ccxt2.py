import os
os.environ["HTTP_PROXY"] = "http://172.18.0.1:7892"
os.environ["HTTPS_PROXY"] = "http://172.18.0.1:7892"

# Try with requests first (not ccxt)
import requests
r = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", timeout=15)
print("Requests:", r.status_code, r.json().get("retCode"))

# Now try ccxt with explicit proxy config
import ccxt
b = ccxt.bybit({
    "proxies": {"http": "http://172.18.0.1:7892", "https": "http://172.18.0.1:7892"}
})
try:
    t = b.fetch_ticker("BTC/USDT")
    print("CCXT:", t["last"])
except Exception as e:
    print("CCXT error:", type(e).__name__, str(e)[:100])
