import sys, json, urllib.request
sys.path.insert(0,"/home/ubuntu/scripts/agents")
proxy = urllib.request.ProxyHandler({"http":"http://127.0.0.1:7891","https":"http://127.0.0.1:7891"})
opener = urllib.request.build_opener(proxy)

# Get Binance futures symbols
try:
    resp = opener.open("https://fapi.binance.com/fapi/v1/exchangeInfo", timeout=10)
    data = json.loads(resp.read())
    binance_symbols = set(s["symbol"] for s in data["symbols"] if s["status"] == "TRADING")
    print("Binance futures symbols:", len(binance_symbols))
except Exception as e:
    print("Binance exchangeInfo failed:", e)
    binance_symbols = set()

our_coins = ["CHZUSDT","IOUSDT","SENTUSDT","ENAUSDT","TAOUSDT","ONDOUSDT","ALLOUSDT",
    "NEARUSDT","INJUSDT","APTUSDT","FETUSDT","AAVEUSDT","TRUMPUSDT","DASHUSDT",
    "ZECUSDT","WLDUSDT","HYPEUSDT","STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT",
    "PORTALUSDT","OPENUSDT","COAIUSDT","MEGAUSDT","CHIPUSDT","KAITOUSDT",
    "ESPORTSUSDT","MITOUSDT","SIRENUSDT","JASMYUSDT","ALGOUSDT","JCTUSDT"]

print("\nMissing from Binance futures:")
missing = [c for c in our_coins if c not in binance_symbols]
for m in missing:
    print("  MISSING:", m)
print("\nPresent on Binance:", len(our_coins) - len(missing), "/", len(our_coins))