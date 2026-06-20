import sys, os, time
sys.path.insert(0, "/home/ubuntu/hermes-v2")
os.chdir("/home/ubuntu/hermes-v2")

from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from core.klines import KlineCache

http = HTTPClient()
ex = ExchangeAPI(http)
kc = KlineCache(ex)

for sym in ["BTCUSDT", "ETHUSDT"]:
    print(f"Fetching {sym}...", end=" ", flush=True)
    t0 = time.time()
    k4 = kc.get(sym, "4h", 300)
    print(f"k4:{len(k4)}", end=" ", flush=True)
    k1 = kc.get(sym, "1h", 300)
    print(f"k1:{len(k1)}", end=" ", flush=True)
    k5 = kc.get(sym, "5m", 50)
    print(f"k5:{len(k5)}", end=" ", flush=True)
    k15 = kc.get(sym, "15m", 30)
    elapsed = time.time() - t0
    print(f"k15:{len(k15)} ({elapsed:.1f}s)")

print("Now testing scorer...")
from indicators.scorer_v2 import ScorerV2
scorer = ScorerV2()

for sym in ["BTCUSDT", "ETHUSDT"]:
    k4 = kc.get(sym, "4h", 300)
    k1 = kc.get(sym, "1h", 300)
    k5 = kc.get(sym, "5m", 50)
    k15 = kc.get(sym, "15m", 30)
    if len(k4) >= 50 and len(k1) >= 50:
        result = scorer.analyze(sym, k4, k1, k5, k15)
        print(f"{sym:12s} score={result['score']:+4d} dir={result['direction']:5s} signal={result['signal']}")
        key_items = {k: v for k, v in result["details"].items() if k in ("rsi_div", "rsi", "momentum", "regime", "bb1h", "st4")}
        print(f"         -> {key_items}")
        if result.get("leading_signals"):
            print(f"         leading: {result['leading_signals']}")
    else:
        print(f"{sym:12s} FAIL - k4:{len(k4)} k1:{len(k1)}")
print("DONE")
