import sys
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import proxy_mgr, BINANCE, fetch_klines, ema, rsi, calc_cvd, bollinger_bands
from datetime import datetime, timezone, timedelta
BJT = timezone(timedelta(hours=8))

def analyze_one(sym):
    try:
        k1 = fetch_klines(sym, '1h', 100)
        if len(k1) < 50: return None
        c = [k['c'] for k in k1]
        rs_arr = rsi(c)
        rs = float(rs_arr[-1]) if isinstance(rs_arr, list) and len(rs_arr) > 0 else 50
        cv = calc_cvd(k1, 6)
        e20_arr = ema(c, 20)
        e50_arr = ema(c, 50)
        e20 = float(e20_arr[-1]) if isinstance(e20_arr, list) and len(e20_arr) > 0 else c[-1]
        e50 = float(e50_arr[-1]) if isinstance(e50_arr, list) and len(e50_arr) > 0 else c[-1]
        price = c[-1]
        trend_1h = 'up' if price > e20 and e20 > e50 else ('down' if price < e20 and e20 < e50 else 'neutral')
        k15 = fetch_klines(sym, '15m', 60)
        trend_15m = 'neutral'
        cv_15m = 0
        if k15 and len(k15) >= 30:
            cv_15m = calc_cvd(k15, 6)
            c15 = [k['c'] for k in k15]
            e15_20 = ema(c15, 20)
            e15_50 = ema(c15, 50)
            if isinstance(e15_20, list) and len(e15_20)>0 and isinstance(e15_50, list) and len(e15_50)>0:
                p15 = c15[-1]
                e20_15 = float(e15_20[-1])
                e50_15 = float(e15_50[-1])
                trend_15m = 'up' if p15 > e20_15 and e20_15 > e50_15 else ('down' if p15 < e20_15 and e20_15 < e50_15 else 'neutral')
        cv_prev = calc_cvd(k1[-12:-6], 6) if len(k1) >= 12 else cv
        cv_delta = cv - cv_prev
        bb_upper, bb_mid, bb_lower, bb_bw = bollinger_bands(c, 20, 2)
        bb_squeeze = bb_bw < 8
        score = 0
        reasons = []
        if cv > 20: score += 10; reasons.append('1hCVD多头'+str(int(cv))+'%')
        elif cv < -20: score -= 10; reasons.append('1hCVD空头'+str(int(cv))+'%')
        elif cv > 10: score += 5; reasons.append('1hCVD偏多'+str(int(cv))+'%')
        elif cv < -10: score -= 5; reasons.append('1hCVD偏空'+str(int(cv))+'%')
        if cv_15m > 20: score += 8; reasons.append('15mCVD多头'+str(int(cv_15m))+'%')
        elif cv_15m < -20: score -= 8; reasons.append('15mCVD空头'+str(int(cv_15m))+'%')
        elif cv_15m > 10: score += 4; reasons.append('15mCVD偏多'+str(int(cv_15m))+'%')
        elif cv_15m < -10: score -= 4; reasons.append('15mCVD偏空'+str(int(cv_15m))+'%')
        if cv > 10 and abs(cv_delta) > 5: score += 10; reasons.append('CVD加速买入')
        elif cv < -10 and abs(cv_delta) > 5: score -= 10; reasons.append('CVD加速卖出')
        if rs < 25: score += 10; reasons.append('RSI超卖'+str(int(rs)))
        elif rs < 35: score += 5; reasons.append('RSI超卖'+str(int(rs)))
        elif rs > 75: score -= 10; reasons.append('RSI超买'+str(int(rs)))
        elif rs > 65: score -= 5; reasons.append('RSI超买'+str(int(rs)))
        if bb_squeeze:
            if cv > 5: score += 8; reasons.append('布林收缩+偏多')
            elif cv < -5: score -= 8; reasons.append('布林收缩+偏空')
            else: reasons.append('布林收缩')
        if trend_1h == 'up' and trend_15m == 'up': score += 12; reasons.append('双周期共振向上')
        elif trend_1h == 'down' and trend_15m == 'down': score -= 12; reasons.append('双周期共振向下')
        elif trend_1h == 'up': score += 6; reasons.append('1h趋势向上')
        elif trend_1h == 'down': score -= 6; reasons.append('1h趋势向下')
        elif trend_15m == 'up': score += 4; reasons.append('15m趋势向上')
        elif trend_15m == 'down': score -= 4; reasons.append('15m趋势向下')
        try:
            k5 = fetch_klines(sym, '5m', 30)
            if k5 and len(k5) >= 10:
                v5 = [k['v'] for k in k5]
                avg5 = sum(v5[-9:-1]) / 8 if len(v5) >= 9 else 1
                if avg5 > 0:
                    vr = v5[-1] / avg5
                    if vr > 2.5: score += 10; reasons.append('5m爆量'+str(round(vr,1))+'x')
                    elif vr > 1.8: score += 6; reasons.append('5m放量'+str(round(vr,1))+'x')
                    elif vr > 1.3: score += 3; reasons.append('5m放量'+str(round(vr,1))+'x')
        except: pass
        sig = 'long' if score >= 10 else ('short' if score <= -10 else 'wait')
        return {'sym':sym,'signal':sig,'score':score,'price':round(price,4),'reasons':reasons,
                'cvd_1h':round(cv,1),'cvd_15m':round(cv_15m,1),'rsi':round(rs,0),
                'trend_1h':trend_1h,'trend_15m':trend_15m,'bb_bw':round(bb_bw,2),'cv_delta':round(cv_delta,1)}
    except Exception as e:
        return {'sym':sym,'error':str(e)}

coins = ['BTCUSDT','ETHUSDT','SOLUSDT','CHZUSDT','DASHUSDT','INJUSDT','TAOUSDT']
for sym in coins:
    r = analyze_one(sym)
    if r and 'error' not in r:
        emoji = {'long': chr(0x1f7e2), 'short': chr(0x1f534), 'wait': chr(0x1f7e1)}.get(r['signal'], '?')
        print(emoji, sym.replace('USDT','').ljust(6), r['signal'].ljust(5), 'score:', str(r['score']).rjust(4), 'price:', r['price'])
        print('  1hCVD:', str(r['cvd_1h']).rjust(5), '%  15mCVD:', str(r['cvd_15m']).rjust(5), '%  delta:', str(r['cv_delta']).rjust(5), '%  RSI:', r['rsi'], ' BB:', r['bb_bw'], '%')
        print('  trend:', r['trend_1h'], '/', r['trend_15m'])
        print('  reasons:', ' | '.join(r['reasons']))
    else:
        print('ERR', sym, r)
    print()
