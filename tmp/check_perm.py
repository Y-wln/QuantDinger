import json, time, hmac, hashlib
from urllib.request import Request, build_opener, ProxyHandler

API_KEY = "YOUR_API_KEY_HERE"
API_SECRET = "YOUR_API_SECRET_HERE"
ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
opener = build_opener(ph)

# Check API key permissions
ts = str(int(time.time() * 1000))
params = "timestamp=" + ts
sig = hmac.new(API_SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()
url = "https://api.binance.com/sapi/v1/account/apiRestrictions?" + params + "&signature=" + sig
req = Request(url, headers={"X-MBX-APIKEY": API_KEY})
try:
    r = opener.open(req, timeout=10)
    data = json.loads(r.read())
    print(json.dumps(data, indent=2))
except Exception as e:
    print("Error:", e)
