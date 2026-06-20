import sys, os, time, signal as sig
sys.path.insert(0, "/home/ubuntu/hermes-v2")
os.chdir("/home/ubuntu/hermes-v2")

from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from core.klines import KlineCache
from core.alerts import Alerts
from core.decision_log import DecisionLog
from indicators.scorer_v2 import ScorerV2
from services.scanner import Scanner

cfg = {"scan_coins": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "scorer_version": "v2",
       "feishu_webhook": "", "log_dir": "/home/ubuntu/hermes-v2/logs",
       "data_dir": "/home/ubuntu/hermes-v2/data"}

http = HTTPClient()
ex = ExchangeAPI(http)
kc = KlineCache(ex)
alerts = Alerts(webhook_url="", log_dir="/home/ubuntu/hermes-v2/logs")
dlog = DecisionLog("/home/ubuntu/hermes-v2/logs")
scorer = ScorerV2()
scanner = Scanner(cfg, kc, scorer, alerts, dlog)

def timeout_handler(signum, frame):
    raise TimeoutError("scan timeout")
sig.signal(sig.SIGALRM, timeout_handler)

print("Testing scanner with 3 coins...")
sig.alarm(60)
try:
    t0 = time.time()
    signals = scanner.scan_all()
    sig.alarm(0)
    elapsed = time.time() - t0
    print(f"DONE in {elapsed:.1f}s. Signals: {len(signals)}")
    for s in signals:
        print(f"  {s['direction']:5s} {s['symbol']:12s} score={s['score']:+4d} price={s['price']}")
except TimeoutError:
    print(f"TIMEOUT after 60s")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback; traceback.print_exc()
