import json
from urllib.request import Request, build_opener, ProxyHandler, urlopen

# Test 7892
try:
    op = build_opener(ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"}))
    r = op.open(Request("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"), timeout=8)
    print("7892 OK:", json.loads(r.read())["price"])
except Exception as e:
    print("7892 FAIL:", e)

# Test 7891
try:
    op = build_opener(ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"}))
    r = op.open(Request("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"), timeout=8)
    print("7891 OK:", json.loads(r.read())["price"])
except Exception as e:
    print("7891 FAIL:", e)

# Test direct
try:
    r = urlopen(Request("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"), timeout=8)
    print("direct OK:", json.loads(r.read())["price"])
except Exception as e:
    print("direct FAIL:", e)
