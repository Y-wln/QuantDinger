import sys
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines, calc_cvd

COINS = ["IOUSDT","ENAUSDT","TAOUSDT","ONDOUSDT","ALLOUSDT","TRUMPUSDT","STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT","COAIUSDT","MEGAUSDT","ESPORTSUSDT","SENTUSDT","JASMYUSDT","ALGOUSDT","FETUSDT","WLDUSDT","HYPEUSDT","INJUSDT","APTUSDT"]

def calc_vwap(k5):
    if not k5: return 0
    tp = 0; tv = 0
    for k in k5[-24:]:
        v = float(k["v"]); typ = (float(k["h"])+float(k["l"])+float(k["c"]))/3
        tp += typ*v; tv += v
    return tp/tv if tv>0 else 0

longs = []
for sym in COINS:
    try:
        k5 = fetch_klines(sym, "5m", 300)
        if not k5 or len(k5)<30: continue
        for i in range(15, len(k5)-6):
            w = k5[:i+1]
            if len(w)<12: continue
            vols = [float(k["v"]) for k in w]
            av = sum(vols[:-3])/max(len(vols)-3,1)
            pc = float(w[-1]["c"]); vw = calc_vwap(w)
            vd = (pc-vw)/vw*100 if vw>0 else 0
            po=float(w[-2]["o"]); pc2=float(w[-2]["c"]); pv=float(w[-2]["v"])
            pch=(pc2-po)/po*100 if po>0 else 0
            co=float(w[-1]["o"]); cc=float(w[-1]["c"])
            cch=(cc-co)/co*100 if co>0 else 0
            vr=pv/max(av,0.001)
            found=False; bs=0
            if vr>=2 and pch<=-2 and cch>=-0.2:
                s=min(int(vr*7+abs(pch)*3),70); found=True; bs=s; entry=pc2
            if len(w)>=8:
                cum=sum((float(w[i2]["c"])-float(w[i2]["o"]))/float(w[i2]["o"])*100 for i2 in range(-5,-2) if float(w[i2]["o"])>0)
                v3s=sum(float(w[i2]["v"]) for i2 in range(-5,-2))
                v3p=sum(float(w[i2]["v"]) for i2 in range(-8,-5))
                v3r=v3s/max(v3p,0.001)
                if cum<=-3 and v3r>=1.8 and cch>=-0.3:
                    s=min(int(v3r*5+abs(cum)*3),65)
                    if s>bs: found=True; bs=s; entry=pc2
            if vd<-5 and cch>=-0.3:
                s=min(int(abs(vd)*5),60)
                if s>bs: found=True; bs=s; entry=pc2
            if found and bs>=20:
                ex=float(k5[i+6]["c"]) if i+6<len(k5) else float(k5[-1]["c"])
                pnl=(ex-entry)/entry*100
                cv5=calc_cvd(w,3)
                red=sum(1 for i2 in range(-5,0) if float(w[i2]["c"])<float(w[i2]["o"]))
                longs.append({"w":pnl>0,"pnl":pnl,"chg":abs(pch),"vr":vr,"cv5":cv5,
                              "scr":bs,"red":red,"vwap":abs(vd) if vd<0 else 0})
    except: pass

print("Total:",len(longs))
# Simple filters
tests = [
    ("ALL", lambda l: True),
    ("chg>=5", lambda l: l["chg"]>=5),
    ("scr>=50", lambda l: l["scr"]>=50),
    ("chg>=4 & vr>=4", lambda l: l["chg"]>=4 and l["vr"]>=4),
    ("chg>=5 or scr>=55", lambda l: l["chg"]>=5 or l["scr"]>=55),
    ("chg>=4 & cv5>=10 & red<=4", lambda l: l["chg"]>=4 and l["cv5"]>=10 and l["red"]<=4),
    ("chg>=3 & vr>=3 & scr>=40", lambda l: l["chg"]>=3 and l["vr"]>=3 and l["scr"]>=40),
    ("vwap>=7", lambda l: l["vwap"]>=7),
]
for name, fn in tests:
    sub = [l for l in longs if fn(l)]
    if sub:
        w = sum(1 for l in sub if l["w"])
        avg = sum(l["pnl"] for l in sub)/len(sub)
        best = max(l["pnl"] for l in sub)
        print("%s: %d sig %.0f%% avg %+.2f%% best %+.2f%%" % (name, len(sub), w/len(sub)*100, avg, best))