import sys; sys.path.insert(0,"/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines
coins = ["IOUSDT","ENAUSDT","TAOUSDT","PLAYUSDT","ALLOSDT","SENTUSDT","COAIUSDT"]
for c in coins:
    k = fetch_klines(c, "5m", 20)
    if k:
        last = k[-1]
        chg = (float(last["c"])-float(last["o"]))/float(last["o"])*100 if float(last["o"])>0 else 0
        print("%s: %d klines, last chg=%.2f%%, v=%s" % (c, len(k), chg, last.get("v","?")))
    else:
        print("%s: FAILED" % c)