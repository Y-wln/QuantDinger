import requests
p = {"http": "http://172.18.0.1:7892", "https": "http://172.18.0.1:7892"}
r = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", proxies=p, timeout=10)
d = r.json()
print("retCode:", d.get("retCode"))
lst = d.get("result",{}).get("list",[])
print("BTC:", lst[0].get("lastPrice") if lst else "none")
