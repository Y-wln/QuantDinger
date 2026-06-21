import requests, json, time
from datetime import datetime, timedelta

proxy = {"http": "http://172.18.0.1:7892", "https": "http://172.18.0.1:7892"}

# Fetch 5m klines for BTC last 2 hours
end = int(time.time() * 1000)
start = end - 7200000  # 2 hours

r = requests.get(
    "https://api.bybit.com/v5/market/kline",
    params={"category": "spot", "symbol": "BTCUSDT", "interval": "5", "start": start, "end": end, "limit": 24},
    proxies=proxy,
    timeout=15
)
d = r.json()
print("retCode:", d.get("retCode"))
klines = d.get("result", {}).get("list", [])
print(f"Got {len(klines)} klines")
for k in klines[:3]:
    ts = datetime.fromtimestamp(int(k[0])/1000)
    print(f"  {ts} O:{k[1]} H:{k[2]} L:{k[3]} C:{k[4]} V:{k[5]}")

# Now test a small coin from MerCu momentum board
for sym in ["BICO", "PORTAL", "JUP"]:
    try:
        r = requests.get(
            "https://api.bybit.com/v5/market/kline",
            params={"category": "spot", "symbol": f"{sym}USDT", "interval": "5", "limit": 3},
            proxies=proxy,
            timeout=10
        )
        d = r.json()
        if d.get("retCode") == 0:
            k = d["result"]["list"]
            print(f"  {sym}: {len(k)} klines, last close={k[0][4] if k else 'none'}")
        else:
            print(f"  {sym}: not listed on Bybit")
    except Exception as e:
        print(f"  {sym}: {e}")
