from urllib.request import Request, build_opener, ProxyHandler
import json
ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
op = build_opener(ph)
r = op.open(Request("https://fapi.binance.com/fapi/v1/forceOrders?symbol=BTCUSDT&limit=3"))
data = json.loads(r.read())
print("Count:", len(data))
if data:
    print(json.dumps(data[0], indent=2))
