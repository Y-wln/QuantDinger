import json, time, hmac, hashlib
from urllib.request import Request, build_opener, ProxyHandler

API_KEY = "YOUR_API_KEY_HERE"
API_SECRET = "YOUR_API_SECRET_HERE"
ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
opener = build_opener(ph)

# Test 1: forceOrders
ts = str(int(time.time() * 1000))
params = "symbol=BTCUSDT&limit=5&timestamp=" + ts
signature = hmac.new(API_SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()
url = "https://fapi.binance.com/fapi/v1/forceOrders?" + params + "&signature=" + signature
print("URL:", url[:100] + "...")
req = Request(url, headers={"X-MBX-APIKEY": API_KEY})
try:
    r = opener.open(req, timeout=15)
    data = json.loads(r.read())
    print("Status:", r.status)
    print("Type:", type(data))
    print("Len:", len(data) if isinstance(data, list) else "N/A")
    if isinstance(data, list) and data:
        print("First:", json.dumps(data[0], indent=2)[:300])
    elif isinstance(data, dict):
        print("Dict:", json.dumps(data, indent=2)[:300])
except Exception as e:
    print("Error:", e)
    # Try to read error body
    try:
        print("Body:", e.read().decode()[:200])
    except:
        pass

# Test 2: openInterest (public, no sign needed)
try:
    url2 = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
    req2 = Request(url2, headers={"User-Agent":"Mozilla/5.0"})
    r2 = opener.open(req2, timeout=10)
    data2 = json.loads(r2.read())
    print("\nOI test OK:", data2)
except Exception as e:
    print("\nOI test FAIL:", e)
