import sys, signal; sys.path.insert(0,"/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines

def timeout_handler(signum, frame):
    raise TimeoutError("Timeout")

coins = ["IOUSDT","ENAUSDT","TAOUSDT","PLAYUSDT","ALLOSDT","SENTUSDT","COAIUSDT","MEGAUSDT","ESPORTSUSDT","CHIPUSDT","KAITOUSDT","MITOUSDT","SIRENUSDT","JCTUSDT","HUMAUSDT"]
for c in coins:
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)
    try:
        k = fetch_klines(c, "5m", 10)
        signal.alarm(0)
        print("%s: OK(%d)" % (c, len(k) if k else 0))
    except Exception as e:
        print("%s: TIMEOUT/ERROR - %s" % (c, str(e)[:50]))