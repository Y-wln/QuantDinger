import sys,json,traceback
sys.path.insert(0, "/home/ubuntu/hermes-v2")
from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from indicators.scorer import Scorer
http=HTTPClient(2,20)
ex=ExchangeAPI(http)
scorer=Scorer()
try:
    k4=ex.klines("BTCUSDT","4h",100)
    k1=ex.klines("BTCUSDT","1h",100)
    k5=ex.klines("BTCUSDT","5m",50)
    k15=ex.klines("BTCUSDT","15m",30)
    print("k4:",len(k4),"k1:",len(k1),"k5:",len(k5),"k15:",len(k15))
    r=scorer.analyze("BTCUSDT",k4,k1,k5,k15)
    print("Score:",r["score"],"Signal:",r["signal"],"Price:",r["price"])
    for k,v in list(r["details"].items())[:8]:
        print(" ",v)
except Exception as e:
    traceback.print_exc()
