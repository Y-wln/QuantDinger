from urllib.request import Request, build_opener, ProxyHandler
import json, time, hmac, hashlib

API_KEY = "YOUR_API_KEY_HERE"
API_SECRET = "YOUR_API_SECRET_HERE"

ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
opener = build_opener(ph)

# Test /fapi/v1/forceOrders with API key
url = "https://fapi.binance.com/fapi/v1/forceOrders?symbol=BTCUSDT&limit=3&timestamp=" + str(int(time.time()*1000))
req = Request(url, headers={
    "X-MBX-APIKEY": API_KEY,
    "User-Agent": "Mozilla/5.0"
})
try:
    r = opener.open(req, timeout=10)
    data = json.loads(r.read())
    print("forceOrders OK:", len(data), "results")
    if data:
        print(json.dumps(data[0], indent=2)[:200])
except Exception as e:
    print("forceOrders FAIL:", e)

# Test account info (verify key works)
url2 = "https://fapi.binance.com/fapi/v2/account?timestamp=" + str(int(time.time()*1000))
signature = hmac.new(API_SECRET.encode(), url2.split('?')[1].encode(), hashlib.sha256).hexdigest()
url2 += "&signature=" + signature
req2 = Request(url2, headers={
    "X-MBX-APIKEY": API_KEY,
    "User-Agent": "Mozilla/5.0"
})
try:
    r2 = opener.open(req2, timeout=10)
    data2 = json.loads(r2.read())
    print("Account OK: totalWalletBalance=", data2.get("totalWalletBalance", "N/A"))
except Exception as e:
    print("Account FAIL:", e)
