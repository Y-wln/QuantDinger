import sys,time; sys.path.insert(0,"/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines, fetch_price

coins = ["IOUSDT","ENAUSDT","TAOUSDT","PLAYUSDT","ONDOUSDT","STGUSDT","MEGAUSDT",
    "COAIUSDT","FETUSDT","WLDUSDT","TRUMPUSDT","AIOUSDT","ALLOUSDT","HYPEUSDT",
    "SYNUSDT","PORTALUSDT","OPENUSDT","CHZUSDT","SENTUSDT","NEARUSDT","INJUSDT",
    "APTUSDT","AAVEUSDT","DASHUSDT","ZECUSDT"]
for c in coins:
    try:
        t0=time.time()
        k=fetch_klines(c,"5m",20)
        dt=time.time()-t0
        if k:
            v=float(k[-2]["v"]); o=float(k[-2]["o"]); cl=float(k[-2]["c"])
            chg=(cl-o)/o*100 if o>0 else 0
            print("%s: OK(%d) %.1fs chg=%.2f%% v=%.0f" % (c,len(k),dt,chg,v))
        else:
            print("%s: EMPTY %.1fs" % (c,dt))
    except Exception as e:
        print("%s: ERR %.1fs - %s" % (c,time.time()-t0,str(e)[:50]))