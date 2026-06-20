import sys, time, traceback
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import (fetch_klines, fetch_oi_history, fetch_taker_volume,
    fetch_long_short_ratio, fetch_funding_rate, fetch_fear_greed,
    ema, rsi, calc_cvd, bollinger_bands, atr)

DEFAULT_PARAMS = {'th': 10, 'sl_atr': 2.0, 'tp_atr': 3.5, 'fast': False}
COIN_PARAMS = {
    'INJUSDT':{'th':8,'sl_atr':3.0,'tp_atr':5.0,'fast':True},
    'CHZUSDT':{'th':8,'sl_atr':3.0,'tp_atr':5.0,'fast':True},
    'DASHUSDT':{'th':8,'sl_atr':3.0,'tp_atr':5.0,'fast':True},
    'TAOUSDT':{'th':10,'sl_atr':2.5,'tp_atr':4.0,'fast':True},
    'FETUSDT':{'th':8,'sl_atr':3.0,'tp_atr':5.0,'fast':True},
    'ENAUSDT':{'th':8,'sl_atr':3.0,'tp_atr':5.0,'fast':True},
    'PEPEUSDT':{'th':8,'sl_atr':3.5,'tp_atr':6.0,'fast':True},
    'WIFUSDT':{'th':8,'sl_atr':3.0,'tp_atr':5.0,'fast':True},
    'BONKUSDT':{'th':8,'sl_atr':3.5,'tp_atr':6.0,'fast':True},
}

def entry_report(sym):
    sym = sym.upper().strip()
    if not sym.endswith('USDT'): sym += 'USDT'
    cp = COIN_PARAMS.get(sym, DEFAULT_PARAMS)
    th = cp['th']; is_fast = cp['fast']
    k1 = fetch_klines(sym, '1h', 100)
    if not k1 or len(k1) < 50: return None
    c = [k['c'] for k in k1]
    rs_arr = rsi(c); rs = float(rs_arr[-1]) if isinstance(rs_arr, list) and len(rs_arr) > 0 else 50
    cv = calc_cvd(k1, 6)
    e20_arr = ema(c, 20); e50_arr = ema(c, 50)
    e20 = float(e20_arr[-1]) if isinstance(e20_arr, list) and len(e20_arr) > 0 else c[-1]
    e50 = float(e50_arr[-1]) if isinstance(e50_arr, list) and len(e50_arr) > 0 else c[-1]
    price = c[-1]
    trend_1h = 'up' if price > e20 and e20 > e50 else ('down' if price < e20 and e20 < e50 else 'neutral')
    k15 = fetch_klines(sym, '15m', 60)
    trend_15m = 'neutral'; cv_15m = 0
    if k15 and len(k15) >= 30:
        cv_15m = calc_cvd(k15, 6)
        c15 = [k['c'] for k in k15]
        e15_20 = ema(c15, 20); e15_50 = ema(c15, 50)
        if isinstance(e15_20,list) and len(e15_20)>0 and isinstance(e15_50,list) and len(e15_50)>0:
            p15=c15[-1]; e20_15=float(e15_20[-1]); e50_15=float(e15_50[-1])
            trend_15m = 'up' if p15>e20_15 and e20_15>e50_15 else ('down' if p15<e20_15 and e20_15<e50_15 else 'neutral')
    cv_prev = calc_cvd(k1[-12:-6], 6) if len(k1)>=12 else cv
    cv_delta = cv - cv_prev
    bb = bollinger_bands(c, 20, 2)
    bb_squeeze = bb.get('squeeze', False) if bb else False
    atr_val = atr(k1, 14)
    score = 0; dims = {}
    if is_fast:
        if cv_15m>20: score+=12; dims['15mCVD']='+12 long '+str(int(cv_15m))+'%'
        elif cv_15m<-20: score-=12; dims['15mCVD']='-12 short '+str(int(cv_15m))+'%'
        elif cv_15m>10: score+=6; dims['15mCVD']='+6 long '+str(int(cv_15m))+'%'
        elif cv_15m<-10: score-=6; dims['15mCVD']='-6 short '+str(int(cv_15m))+'%'
        if cv>20: score+=6; dims['1hCVD']='+6 long '+str(int(cv))+'%'
        elif cv<-20: score-=6; dims['1hCVD']='-6 short '+str(int(cv))+'%'
    else:
        if cv>20: score+=10; dims['1hCVD']='+10 long '+str(int(cv))+'%'
        elif cv<-20: score-=10; dims['1hCVD']='-10 short '+str(int(cv))+'%'
        elif cv>10: score+=5; dims['1hCVD']='+5 long '+str(int(cv))+'%'
        elif cv<-10: score-=5; dims['1hCVD']='-5 short '+str(int(cv))+'%'
        if cv_15m>20: score+=6; dims['15mCVD']='+6 long '+str(int(cv_15m))+'%'
        elif cv_15m<-20: score-=6; dims['15mCVD']='-6 short '+str(int(cv_15m))+'%'
    if cv>10 and abs(cv_delta)>5: score+=10; dims['CVDaccel']='+10 buy'
    elif cv<-10 and abs(cv_delta)>5: score-=10; dims['CVDaccel']='-10 sell'
    if rs<25: score+=10; dims['RSI']='+10 oversold '+str(int(rs))
    elif rs<35: score+=5; dims['RSI']='+5 oversold '+str(int(rs))
    elif rs>75: score-=10; dims['RSI']='-10 overbought '+str(int(rs))
    elif rs>65: score-=5; dims['RSI']='-5 overbought '+str(int(rs))
    else: dims['RSI']='0 neutral '+str(int(rs))
    if bb_squeeze:
        if cv>5: score+=8; dims['BB']='+8 squeeze+long'
        elif cv<-5: score-=8; dims['BB']='-8 squeeze+short'
    if trend_1h=='up' and trend_15m=='up': score+=12; dims['Trend']='+12 both up'
    elif trend_1h=='down' and trend_15m=='down': score-=12; dims['Trend']='-12 both down'
    elif trend_1h=='up': score+=6; dims['Trend']='+6 1h up'
    elif trend_1h=='down': score-=6; dims['Trend']='-6 1h down'
    elif trend_15m=='up': score+=4; dims['Trend']='+4 15m up'
    elif trend_15m=='down': score-=4; dims['Trend']='-4 15m down'
    try:
        oi_hist = fetch_oi_history(sym, '5m', 5)
        if oi_hist and len(oi_hist)>=4:
            oi_c = (oi_hist[-1]-oi_hist[0])/oi_hist[0]*100 if oi_hist[0]>0 else 0
            pc = (c[-1]-c[-6])/c[-6]*100 if len(c)>=6 else 0
            if oi_c>2 and abs(pc)<=0.5: score+=12; dims['OI']='+12 accumulation'
            elif oi_c<-2 and abs(pc)<=0.5: score-=12; dims['OI']='-12 distribution'
            elif oi_c>2: score+=6; dims['OI']='+6 long build'
            elif oi_c<-2: score-=6; dims['OI']='-6 short build'
    except: pass
    try:
        taker = fetch_taker_volume(sym)
        td = taker.get('trend','neutral') if taker else 'neutral'
        if td=='bullish': score+=8; dims['Taker']='+8 buy'
        elif td=='bearish': score-=8; dims['Taker']='-8 sell'
    except: pass
    try:
        lsr = fetch_long_short_ratio(sym)
        if lsr>2.5: score-=6; dims['LSR']='-6 crowd long'
        elif lsr<0.5: score+=6; dims['LSR']='+6 crowd short'
    except: pass
    try:
        fr = fetch_funding_rate(sym)
        if fr<-0.001: score+=6; dims['Funding']='+6 squeeze long'
        elif fr>0.003: score-=6; dims['Funding']='-6 squeeze short'
    except: pass
    try:
        fng = fetch_fear_greed()
        dims['FnG'] = str(fng)
    except: pass
    sig = 'long' if score>=th else ('short' if score<=-th else 'wait')
    entry_ok = True; entry_note = ''
    if sig=='long':
        ext = (price-e20)/e20*100 if e20 else 0
        if ext>2.0: entry_ok=False; entry_note='Price >2% above EMA20, wait for pullback to '+str(round(e20,4))
        elif ext>1.0: entry_note='Price slightly above EMA20, light position OK'
        if rs>70: entry_ok=False; entry_note+='; RSI hot('+str(int(rs))+')'
    elif sig=='short':
        ext = (e20-price)/e20*100 if e20 else 0
        if ext>2.0: entry_ok=False; entry_note='Price >2% below EMA20, wait for bounce to '+str(round(e20,4))
        elif ext>1.0: entry_note='Price slightly below EMA20, light position OK'
        if rs<30: entry_ok=False; entry_note+='; RSI cold('+str(int(rs))+')'
    sl_p = price-atr_val*cp['sl_atr'] if sig=='long' else price+atr_val*cp['sl_atr']
    tp_p = price+atr_val*cp['tp_atr'] if sig=='long' else price-atr_val*cp['tp_atr']
    return {'sym':sym.replace('USDT',''), 'signal':sig, 'score':score,
        'price':round(price,4), 'dims':dims, 'entry_ok':entry_ok,
        'entry_note':entry_note, 'e20':round(e20,4), 'atr':round(atr_val,4),
        'sl':round(sl_p,4), 'tp':round(tp_p,4)}
