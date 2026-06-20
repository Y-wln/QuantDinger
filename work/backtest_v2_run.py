#!/usr/bin/env python3
"""小鹿策略v2 历史回测 — 过去30天每4h分析"""
import os, math, json
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
import requests
import numpy as np

S = requests.Session()
S.proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
B = "https://api.binance.com"

def fetch(symbol, interval, limit=700):
    r = S.get(f"{B}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}", timeout=15).json()
    return [{"o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "v": float(k[5]), "t": int(k[0])} for k in r]

# 把策略里的函数全搬过来（精简版）
def ema(v, p):
    if len(v)<p: return None
    k=2/(p+1); r=v[0]
    for x in v[1:]: r=x*k+r*(1-k)
    return r
def ema_s(v,p):
    if len(v)<p: return [None]*len(v)
    k=2/(p+1); r=[None]*len(v); r[p-1]=sum(v[:p])/p
    for i in range(p,len(v)): r[i]=v[i]*k+r[i-1]*(1-k)
    return r
def rsi_val(c,p=14):
    if len(c)<p+1: return 50
    ch=[c[i]-c[i-1] for i in range(1,len(c))]
    ag=sum(x for x in ch[:p] if x>0)/p; al=sum(-x for x in ch[:p] if x<0)/p
    if al==0: return 100
    for i in range(p,len(ch)):
        x=ch[i]; ag=(ag*(p-1)+max(x,0))/p; al=(al*(p-1)+max(-x,0))/p
    return 50 if al==0 else 100-100/(1+ag/al)
def atr_v(h,l,c,p=14):
    n=len(c); tr=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,n)]
    return sum(tr[-p:])/p if len(tr)>=p else 0

def vegas(c):
    if len(c)<676: return None
    e12,e144,e169,e576,e676=ema(c,12),ema(c,144),ema(c,169),ema(c,576),ema(c,676)
    cur=c[-1]
    if cur>e144>e169 and e144>e576 and e169>e676: d="强势多头"
    elif cur>e144>e169: d="多头"
    elif cur<e144<e169 and e144<e576 and e169<e676: d="强势空头"
    elif cur<e144<e169: d="空头"
    else: d="震荡"
    return {"dir":d,"e144":e144,"e169":e169,"cw":round((e169-e144)/e144*100,2) if e144 else 0}

def choppiness(h,l,c,p=14):
    n=len(c)
    if n<p+1: return None
    tr=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,n)]
    tr.insert(0,tr[0] if tr else 0)
    watr=sum(tr[-p:]); hh=max(h[-p:]); ll=min(l[-p:])
    if hh==ll: return {"ci":50,"regime":"震荡"}
    ci=100*math.log10(watr/(hh-ll))/math.log10(p)
    ci=max(0,min(100,ci))
    if ci>61.8: reg="震荡"
    elif ci<38.2: reg="趋势"
    else: reg="过渡"
    return {"ci":round(ci,1),"regime":reg}

def bos_choch(h,l,c,lb=7):
    n=len(c)
    if n<lb*2+1: return None
    sh,sl=[],[]
    for i in range(lb,n-lb):
        if all(h[i]>=h[j] for j in range(i-lb,i+lb+1) if j!=i): sh.append((i,h[i]))
        if all(l[i]<=l[j] for j in range(i-lb,i+lb+1) if j!=i): sl.append((i,l[i]))
    breaks,struc=[],"未知"
    for i in range(len(sh)):
        for j in range(i+1,len(sh)):
            if sh[j][1]>sh[i][1]: breaks.append({"t":"bull","p":sh[j][1]}); struc="上升"
            elif sh[j][1]<sh[i][1]: breaks.append({"t":"bear_struct","p":sh[j][1]}); struc="下降"
    for i in range(len(sl)):
        for j in range(i+1,len(sl)):
            if sl[j][1]<sl[i][1]: breaks.append({"t":"bear","p":sl[j][1]}); struc="下降"
            elif sl[j][1]>sl[i][1]: breaks.append({"t":"bull_struct","p":sl[j][1]}); struc="上升"
    return {"str":struc,"last":breaks[-1] if breaks else None}

def supertrend(h,l,c,p=10,mult=3.0):
    n=len(c)
    if n<p+1: return None
    tr=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,n)]
    tr.insert(0,tr[0] if tr else 0)
    atr_s=[0.0]*n
    for i in range(p,n): atr_s[i]=sum(tr[i-p+1:i+1])/p
    hl=[(h[i]+l[i])/2 for i in range(n)]
    up,lo,trend=[0.0]*n,[0.0]*n,[0]*n
    for i in range(p,n):
        up[i]=hl[i]+mult*atr_s[i]; lo[i]=hl[i]-mult*atr_s[i]
        if i>p:
            up[i]=min(up[i],up[i-1]) if c[i-1]>up[i-1] else up[i]
            lo[i]=max(lo[i],lo[i-1]) if c[i-1]<lo[i-1] else lo[i]
        trend[i]=1 if c[i]>(up[i-1] if i>p else up[i]) else (-1 if c[i]<(lo[i-1] if i>p else lo[i]) else (trend[i-1] if i>p else 0))
    return {"dir":"多头" if trend[-1]==1 else "空头","atr":round(atr_s[-1],2)}

def macd(c,fast=12,slow=26,sig=9):
    if len(c)<slow+sig: return None
    fe=ema_s(c,fast); se=ema_s(c,slow)
    ml=[fe[i]-se[i] if fe[i] and se[i] else 0 for i in range(len(c))]
    sl=ema_s(ml,sig)
    h=ml[-1]-sl[-1] if sl[-1] else 0
    if ml[-1]>sl[-1]: s="bullish"
    elif ml[-1]<sl[-1]: s="bearish"
    else: s="neutral"
    return {"sig":s,"hist":round(h,4),"macd":round(ml[-1],4)}

def kdj(h,l,c,n=9):
    if len(c)<n: return None
    kv,dv=[50.0]*n,[50.0]*n
    for i in range(n,len(c)):
        hh=max(h[i-n+1:i+1]); ll=min(l[i-n+1:i+1])
        rsv=(c[i]-ll)/(hh-ll)*100 if hh!=ll else 50
        kv.append(2/3*kv[-1]+1/3*rsv)
        dv.append(2/3*dv[-1]+1/3*kv[-1])
    k,d=kv[-1],dv[-1]; j=3*k-2*d
    if k<20 and d<20: z="超卖"
    elif k>80 and d>80: z="超买"
    else: z="中性"
    return {"k":round(k,1),"d":round(d,1),"j":round(j,1),"zone":z}

def bollinger(c,period=20,sd=2):
    if len(c)<period: return None
    m=np.mean(c[-period:]); s=np.std(c[-period:])
    u=m+sd*s; l=m-sd*s; cur=c[-1]
    pb=(cur-l)/(u-l) if u-l>0 else 0.5
    return {"upper":round(u,2),"mid":round(m,2),"lower":round(l,2),"pb":round(pb,3)}

def consensus(v,ci,bos,st,macd_r,kdj_r,bb,rsi_v):
    score=0; reasons=[]
    if v and v["dir"] in ("强势多头","多头"): score+=25; reasons.append("维加斯多头+25")
    elif v and v["dir"] in ("强势空头","空头"): score-=25; reasons.append("维加斯空头-25")
    if ci and ci["regime"]=="趋势": score+=10; reasons.append("趋势行情+10")
    elif ci: score+=3; reasons.append("震荡+3")
    if bos and bos["str"]=="上升": score+=15; reasons.append("上升结构+15")
    elif bos and bos["str"]=="下降": score-=15; reasons.append("下降结构-15")
    if bos and bos["last"]:
        if bos["last"]["t"]=="bear_struct": score-=8; reasons.append("结构破位-8")
        elif bos["last"]["t"]=="bull_struct": score+=8; reasons.append("结构突破+8")
    if st and st["dir"]=="多头": score+=10; reasons.append("SuperTrend多头+10")
    elif st: score-=10; reasons.append("SuperTrend空头-10")
    if macd_r and macd_r["sig"]=="bullish": score+=8; reasons.append("MACD看涨+8")
    elif macd_r and macd_r["sig"]=="bearish": score-=8; reasons.append("MACD看跌-8")
    if kdj_r and kdj_r["zone"]=="超卖": score+=7; reasons.append("KDJ超卖+7")
    elif kdj_r and kdj_r["zone"]=="超买": score-=7; reasons.append("KDJ超买-7")
    if bb and bb["pb"]<0.2: score+=8; reasons.append("布林下轨+8")
    elif bb and bb["pb"]>0.8: score-=8; reasons.append("布林上轨-8")
    if 40<rsi_v<75: score+=5; reasons.append(f"RSI{rsi_v:.0f}健康+5")
    if ci and ci["regime"]=="趋势":
        if score>0: score+=5
        elif score<0: score-=5
    score=max(-100,min(100,score))
    sig="📈偏多" if score>20 else ("📉偏空" if score<-20 else "📊中性")
    return {"score":score,"sig":sig,"reasons":reasons}

from datetime import datetime,timezone,timedelta
BJT=timezone(timedelta(hours=8))

for sym in ["BTCUSDT","ETHUSDT","SOLUSDT"]:
    print(f"\n{'='*50}")
    print(f"  {sym} 30天回测")
    print(f"{'='*50}")
    kl=fetch(sym,"4h",700)
    if len(kl)<200: print(f"  数据不足"); continue
    
    step=10; results=[]
    for i in range(200,len(kl),step):
        w=kl[:i+1]
        c=[k["c"] for k in w]; h=[k["h"] for k in w]; l=[k["l"] for k in w]
        v=vegas(c); ci=choppiness(h,l,c)
        bos=bos_choch(h,l,c); st=supertrend(h,l,c)
        macd_r=macd(c); kdj_r=kdj(h,l,c); bb=bollinger(c)
        rsi=rsi_val(c); atr=atr_v(h,l,c)
        cs=consensus(v,ci,bos,st,macd_r,kdj_r,bb,rsi)
        ts=datetime.fromtimestamp(w[-1]["t"]/1000,tz=BJT).strftime("%m-%d %H:%M")
        results.append({"t":ts,"p":c[-1],"cs":cs,"v":v,"rsi":rsi,"atr":atr})
    
    for r in results[-10:]:
        emoji={"📈偏多":"🟢","📉偏空":"🔴","📊中性":"🟡"}.get(r["cs"]["sig"],"⚪")
        print(f"\n  {emoji} {r['t']} | \ | {r['cs']['sig']} {r['cs']['score']:+.0f}")
        if r["v"]: print(f"  维加斯:{r['v']['dir']} | RSI:{r['rsi']:.0f} | ATR:{r['atr']:.2f}")
        for reason in r["cs"]["reasons"][:4]:
            print(f"    {reason}")

print("\n"+"="*50)
print("回测完成 — 仅客观数据")

