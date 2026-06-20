import sys,json,traceback,time
sys.path.insert(0, "/home/ubuntu/hermes-v2")
from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from indicators.scorer import Scorer
http=HTTPClient(2,20)
ex=ExchangeAPI(http)
scorer=Scorer()
coins=["BTCUSDT","ETHUSDT","SOLUSDT","DOGEUSDT","LINKUSDT","AVAXUSDT","FETUSDT","TRUMPUSDT"]
print("=== V2 Signal Test", time.strftime("%Y-%m-%d %H:%M:%S"), "===")
for sym in coins:
    try:
        k4=ex.klines(sym,"4h",100)
        k1=ex.klines(sym,"1h",100)
        k5=ex.klines(sym,"5m",50)
        k15=ex.klines(sym,"15m",30)
        r=scorer.analyze(sym,k4,k1,k5,k15)
        d=r["direction"].upper()
        e="LONG" if d=="LONG" else ("SHORT" if d=="SHORT" else "WAIT")
        print(f"{sym:12s} Score:{r['score']:+4d}  {e:6s}  ${r['price']:.4f}  {len(r['leading_signals'])} leading")
        for k,v in list(r["details"].items())[:5]:
            print(f"  {v}")
    except Exception as e:
        print(f"{sym:12s} FAIL: {e}")
    print()
