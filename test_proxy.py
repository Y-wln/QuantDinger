import os, requests
proxies = {"http": "http://host.docker.internal:7892", "https": "http://host.docker.internal:7892"}
r = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", proxies=proxies, timeout=10)
d = r.json()
print("retCode:", d.get("retCode"))
lst = d.get("result",{}).get("list",[])
if lst: print("BTC:", lst[0].get("lastPrice"))
