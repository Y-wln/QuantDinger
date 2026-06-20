#!/usr/bin/env python3
"""????? v14 - ?????? + ????? + ??????"""
import sys, os, time, json
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import (proxy_mgr, BINANCE, BINANCE_F, feishu_send, feishu_app_send, bollinger_bands, atr,
    fetch_klines, fetch_oi, fetch_funding_rate, ema, rsi, calc_cvd, fetch_oi_history, fetch_taker_volume,
    fetch_long_short_ratio, fetch_fear_greed, fetch_orderbook_imbalance, fetch_1m_cvd)
from entry_report import DEFAULT_PARAMS, COIN_PARAMS
BJT = timezone(timedelta(hours=8))

SKIP = {'BTC','ETH','SOL','BNB','XRP','ADA','DOGE','DOT','LINK','AVAX','LTC',
    'USDC','USDT','DAI','BUSD','TUSD','FDUSD','WBTC','STETH'}
MAX_POS = 5
STATE_FILE = '/home/ubuntu/scripts/yaobi_state.json'

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except: return {'positions':{}, 'pnl':0.0, 'trades':0}

def save_state(st):
    try:
        with open(STATE_FILE,'w') as f: json.dump(st, f, indent=2, default=str)
    except: pass

# ====== v14: ?????? ======
def get_candidates():
    candidates = {}
    
    # ?1?: 24hr??? (???????)
    try:
        data24 = proxy_mgr.fetch_json(BINANCE_F + '/fapi/v1/ticker/24hr', 12)
        if data24:
            for t in data24:
                sym = t.get('symbol','')
                if not sym.endswith('USDT'): continue
                name = sym.replace('USDT','')
                if name in SKIP: continue
                try:
                    vol = float(t.get('quoteVolume',0))
                    chg = float(t.get('priceChangePercent',0))
                    if vol > 5e5 and abs(chg) > 2:
                        score = abs(chg) * 0.4
                        candidates[sym] = (vol, score, chg)
                except: pass
    except: pass

    # ?2?: 5m K??? (????) - ??30???,???
    scan_list = list(candidates.keys())[:15]
    try:
        books = proxy_mgr.fetch_json(BINANCE_F + '/fapi/v1/ticker/bookTicker', 6)
        if books:
            for b in books[:60]:
                sym = b.get('symbol','')
                if sym.endswith('USDT'):
                    name = sym.replace('USDT','')
                    if name not in SKIP and sym not in scan_list:
                        scan_list.append(sym)
    except: pass
    scan_list = scan_list[:35]

    def _scan_5m(sym):
        try:
            k5 = fetch_klines(sym, '5m', 12)
            if not k5 or len(k5) < 8: return None
            cv5 = calc_cvd(k5, 6)
            c5 = [k['c'] for k in k5]
            chg5 = (c5[-1] - c5[0]) / c5[0] * 100 if c5[0] > 0 else 0
            v5 = [k['v'] for k in k5]
            avg_v = sum(v5[-5:-1]) / 4 if len(v5) >= 5 else 1
            vr = v5[-1] / avg_v if avg_v > 0 else 1
            score = abs(cv5) * 0.6 + abs(chg5) * 0.4 + min(vr * 2, 10)
            return (sym, score, cv5, chg5, vr)
        except:
            return None

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_scan_5m, s): s for s in scan_list}
        for f in as_completed(futures, timeout=15):
            res = f.result()
            if res:
                sym, score, cv5, chg5, vr = res
                if score > 3:
                    if sym in candidates:
                        old = candidates[sym]
                        candidates[sym] = (old[0], old[1] + score, old[2])
                    else:
                        candidates[sym] = (0, score, chg5)

    # ?3?: Orderbook?? (????)
    top_candidates = sorted(candidates.items(), key=lambda x: x[1][1], reverse=True)[:12]
    def _scan_ob(sym):
        try:
            ob = fetch_orderbook_imbalance(sym)
            if ob:
                imb = abs(ob.get('imbalance', 0))
                if imb > 20:
                    return (sym, imb * 0.3)
        except: pass
        return None

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_scan_ob, s): s for s, _ in top_candidates}
        for f in as_completed(futures, timeout=10):
            res = f.result()
            if res:
                sym, bonus = res
                if sym in candidates:
                    old = candidates[sym]
                    candidates[sym] = (old[0], old[1] + bonus, old[2])

    result = sorted(candidates.items(), key=lambda x: x[1][1], reverse=True)
    final = [(sym, vol, chg) for sym, (vol, score, chg) in result[:25]]
    return final

def analyze_one(sym):
    try:
        cp = COIN_PARAMS.get(sym, DEFAULT_PARAMS)
        th = cp['th']

        k1 = fetch_klines(sym, '1h', 100)
        if len(k1) < 50: return None
        c = [k['c'] for k in k1]
        rs = rsi(c)
        cv = calc_cvd(k1, 6)
        e20_arr = ema(c, 20)
        e50_arr = ema(c, 50)
        e20 = float(e20_arr[-1]) if isinstance(e20_arr, list) and len(e20_arr) > 0 else c[-1]
        e50 = float(e50_arr[-1]) if isinstance(e50_arr, list) and len(e50_arr) > 0 else c[-1]
        price = c[-1]
        trend_1h = 'up' if price > e20 and e20 > e50 else ('down' if price < e20 and e20 < e50 else 'neutral')

        trend_15m = 'neutral'
        cv_15m = 0
        k15 = fetch_klines(sym, '15m', 60)
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

        bb = bollinger_bands(c, 20, 2)
        bb_bw = bb["bandwidth"] if bb else 50
        bb_squeeze = bb.get("squeeze", False) if bb else False

        atr_val = atr(k1, 14)

        score = 0
        reasons = []

        # ====== v14: ????? (?????,????) ======
        flash_triggered = False
        flash_hits = []

        try:
            cvd1m_val = fetch_1m_cvd(sym)
            if cvd1m_val > 50:
                flash_hits.append(('long', '1mCVD??{}%'.format(int(cvd1m_val))))
                flash_triggered = True
            elif cvd1m_val < -50:
                flash_hits.append(('short', '1mCVD??{}%'.format(int(abs(cvd1m_val)))))
                flash_triggered = True
            elif cvd1m_val > 30:
                flash_hits.append(('long', '1mCVD?{}%'.format(int(cvd1m_val))))
            elif cvd1m_val < -30:
                flash_hits.append(('short', '1mCVD?{}%'.format(int(abs(cvd1m_val)))))
        except Exception:
            pass

        try:
            ob_val = fetch_orderbook_imbalance(sym)
            if ob_val:
                imb = ob_val.get('imbalance', 0)
                if imb > 30:
                    flash_hits.append(('long', '????{}%'.format(imb)))
                    flash_triggered = True
                elif imb < -30:
                    flash_hits.append(('short', '????{}%'.format(abs(imb))))
                    flash_triggered = True
                elif imb > 20:
                    flash_hits.append(('long', '????{}%'.format(imb)))
                elif imb < -20:
                    flash_hits.append(('short', '????{}%'.format(abs(imb))))
        except Exception:
            pass

        # ====== v13: ?????? (60%) ======

        # 1. 5m???CVD
        cv5 = 0
        k5 = None
        try:
            k5 = fetch_klines(sym, '5m', 30)
            if k5 and len(k5) >= 10:
                cv5 = calc_cvd(k5, 3)
                if cv5 > 25: score += 14; reasons.append('5mCVD??'+str(int(cv5))+'%')
                elif cv5 < -25: score -= 14; reasons.append('5mCVD??'+str(int(abs(cv5)))+'%')
                elif cv5 > 12: score += 7; reasons.append('5mCVD??')
                elif cv5 < -12: score -= 7; reasons.append('5mCVD??')
        except: pass

        # 2. 15m CVD
        if cv_15m > 20: score += 8; reasons.append('15mCVD??'+str(int(cv_15m))+'%')
        elif cv_15m < -20: score -= 8; reasons.append('15mCVD??'+str(int(cv_15m))+'%')
        elif cv_15m > 10: score += 4; reasons.append('15mCVD??')
        elif cv_15m < -10: score -= 4; reasons.append('15mCVD??')

        # 3. CVD??
        if cv_delta > 10: score += 8; reasons.append('CVD????')
        elif cv_delta < -10: score -= 8; reasons.append('CVD????')
        elif cv_delta > 5: score += 4; reasons.append('CVD??')
        elif cv_delta < -5: score -= 4; reasons.append('CVD??')

        # 4. 5m??
        try:
            if k5 and len(k5) >= 10:
                v5 = [k['v'] for k in k5]
                avg5 = sum(v5[-9:-1]) / 8 if len(v5) >= 9 else 1
                if avg5 > 0:
                    vr = v5[-1] / avg5
                    if vr > 3.0: score += 12; reasons.append('5m??'+str(round(vr,1))+'x')
                    elif vr > 2.0: score += 8; reasons.append('5m??'+str(round(vr,1))+'x')
                    elif vr > 1.5: score += 4; reasons.append('5m???')
        except: pass

        # 5. BB??
        if bb_squeeze:
            if cv5 > 5 or cv_15m > 5: score += 10; reasons.append('BB??+??')
            elif cv5 < -5 or cv_15m < -5: score -= 10; reasons.append('BB??+??')
            else: score += 6; reasons.append('BB??????')

        # ====== ???? ======

        # 6. 1h CVD (??)
        if cv > 30: score += 6; reasons.append('1hCVD??')
        elif cv < -30: score -= 6; reasons.append('1hCVD??')
        elif cv > 15: score += 3; reasons.append('1hCVD??')
        elif cv < -15: score -= 3; reasons.append('1hCVD??')

        # 7. RSI (??)
        if rs < 20: score += 8; reasons.append('RSI???')
        elif rs < 30: score += 5; reasons.append('RSI??')
        elif rs > 80: score -= 8; reasons.append('RSI???')
        elif rs > 70: score -= 5; reasons.append('RSI??')
        elif rs > 55: score += 3
        else: score -= 3

        # 8. 15m??
        if trend_15m == 'up': score += 5; reasons.append('15m????')
        elif trend_15m == 'down': score -= 5; reasons.append('15m????')

        # === Leading indicators ===
        # OI
        try:
            oi_hist = fetch_oi_history(sym, '5m', 5)
            if oi_hist and len(oi_hist) >= 4:
                oi_c = (oi_hist[-1] - oi_hist[0]) / oi_hist[0] * 100 if oi_hist[0] > 0 else 0
                pc = (c[-1] - c[-6]) / c[-6] * 100 if len(c) >= 6 else 0
                if oi_c > 2 and abs(pc) <= 0.5:
                    score += 12; reasons.append('OI????(??OI?)')
                elif oi_c < -2 and abs(pc) <= 0.5:
                    score -= 12; reasons.append('OI????(??OI?)')
                elif oi_c > 2 and pc > 0.5:
                    if score > 0: score += 6; reasons.append('OI????')
                elif oi_c < -2 and pc < -0.5:
                    if score < 0: score -= 6; reasons.append('OI????')
        except Exception: pass

        # Taker
        try:
            taker = fetch_taker_volume(sym)
            td = taker.get('trend', 'neutral') if taker else 'neutral'
            if td == 'bullish': score += 8; reasons.append('??????')
            elif td == 'bearish': score -= 8; reasons.append('??????')
        except Exception: pass

        # LSR
        try:
            lsr = fetch_long_short_ratio(sym)
            if lsr > 2.5: score -= 6; reasons.append('??????')
            elif lsr < 0.5: score += 6; reasons.append('??????')
        except Exception: pass

        # FR
        try:
            fr = fetch_funding_rate(sym)
            if fr < -0.001: score += 6; reasons.append('????(??)')
            elif fr > 0.003: score -= 6; reasons.append('????(??)')
        except Exception: pass

        # FnG
        try:
            fng = fetch_fear_greed()
            td = trend_1h == 'down'
            ts = trend_1h == trend_15m and trend_1h != 'neutral'
            if fng <= 20:
                if td: score -= 10 if ts else 7; reasons.append('????+??(???)')
                elif trend_1h == 'up': score += 10 if ts else 7; reasons.append('??????(???)')
                else: score += 4; reasons.append('??????(??)')
            elif fng <= 35:
                if td: score -= 5 if ts else 3
                elif trend_1h == 'up': score += 5 if ts else 3
                else: score += 2
            elif fng >= 80:
                if not td: score += 10 if ts else 7; reasons.append('????+??(???)')
                elif trend_1h == 'down': score -= 10 if ts else 7; reasons.append('??????(???)')
                else: score -= 4; reasons.append('??????(??)')
            elif fng >= 65:
                if not td: score += 5 if ts else 3
                elif trend_1h == 'down': score -= 5 if ts else 3
                else: score -= 2
        except Exception: pass

        # CVD-????
        try:
            if len(c) >= 12:
                price_d = (c[-1] - c[-6]) / c[-6] * 100 if c[-6] > 0 else 0
                cv1h = calc_cvd(k1, 6)
                if cv1h > 35 and price_d < -0.5:
                    score += 6; reasons.append('CVD???:????')
                elif cv1h < -35 and price_d > 0.5:
                    score -= 6; reasons.append('CVD???:????')
        except Exception: pass

        sig = 'long' if score >= th else ('short' if score <= -th else 'wait')

        # ====== v14: ??????? (2????? = ??) ======
        if sig == 'wait':
            long_hits = [r for d, r in flash_hits if d == 'long']
            short_hits = [r for d, r in flash_hits if d == 'short']
            if len(long_hits) >= 2:
                sig = 'long'; score = 24; reasons = long_hits
            elif len(short_hits) >= 2:
                sig = 'short'; score = -24; reasons = short_hits

        # Entry quality
        entry_warnings = []
        if sig == 'long':
            ext_pct = (price - e20) / e20 * 100 if e20 else 0
            if ext_pct > 1.5:
                entry_warnings.append('????EMA20 '+str(round(ext_pct,1))+'%')
            if rs > 75:
                entry_warnings.append('RSI??'+str(int(rs)))
        elif sig == 'short':
            ext_pct = (e20 - price) / e20 * 100 if e20 else 0
            if ext_pct > 1.5:
                entry_warnings.append('????EMA20 '+str(round(ext_pct,1))+'%')
            if rs < 25:
                entry_warnings.append('RSI??'+str(int(rs)))

        return {'sym': sym, 'signal': sig, 'score': score, 'price': price,
            'reasons': reasons, 'cvd': round(cv,1), 'rsi': round(rs,0), 'trend': trend_1h,
            'atr': round(atr_val, 4), 'params': cp, 'entry_ok': True,
            'entry_zone': price, 'entry_warnings': entry_warnings,
            'flash': len(flash_hits) > 0, 'flash_hits': flash_hits}
    except Exception as e:
        return None

def scan():
    t0 = time.time()
    now = datetime.now(BJT)
    state = load_state()
    positions = state.get('positions', {})

    candidates = get_candidates()
    if not candidates:
        print('[{}] ???????'.format(now.strftime('%H:%M:%S')))
        return

    signals = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {}
        for sym, vol, chg in candidates[:25]:
            futures[ex.submit(analyze_one, sym)] = sym
        for f in as_completed(futures, timeout=25):
            res = f.result()
            if res and res['signal'] != 'wait':
                signals.append(res)

    # ???????
    signals.sort(key=lambda s: (not s.get('flash', False), -abs(s['score'])))

    new_trades = 0
    alerts = []

    for s in signals:
        sym = s['sym']
        if sym in positions:
            continue
        if len(positions) >= MAX_POS:
            break

        flash_tag = 'FLASH' if s.get('flash') else ''
        if s['signal'] == 'long':
            alerts.append('LONG|{}|{}|{}|{}|{}|{}'.format(sym, s['score'], round(s['cvd'],1), int(s['rsi']), round(s['price'],4), flash_tag))
            atr_s = s.get('atr', 0.01); pat = s.get('params', DEFAULT_PARAMS)
            positions[sym] = {'direction':'long','entry':s['price'],'sl':s['price']-atr_s*pat['sl_atr']*2.5,
                'tp':s['price']+atr_s*pat['tp_atr'],'time':now.isoformat(),'reasons':s['reasons']}
            new_trades += 1
        elif s['signal'] == 'short':
            alerts.append('SHORT|{}|{}|{}|{}|{}|{}'.format(sym, s['score'], round(s['cvd'],1), int(s['rsi']), round(s['price'],4), flash_tag))
            atr_s = s.get('atr', 0.01); pat = s.get('params', DEFAULT_PARAMS)
            positions[sym] = {'direction':'short','entry':s['price'],'sl':s['price']+atr_s*pat['sl_atr']*2.5,
                'tp':s['price']-atr_s*pat['tp_atr'],'time':now.isoformat(),'reasons':s['reasons']}
            new_trades += 1

    # ??/??
    closed = []
    for sym, p in list(positions.items()):
        price = 0
        try:
            data = proxy_mgr.fetch_json(BINANCE_F + '/fapi/v1/ticker/price?symbol=' + sym, 8)
            price = float(data.get('price', 0))
        except: continue
        if not price: continue
        if p['direction'] == 'long':
            if price <= p['sl']:
                pnl = (price - p['entry']) / p['entry'] * 100
                closed.append((sym, '??', pnl))
                del positions[sym]
            elif price >= p['tp']:
                pnl = (price - p['entry']) / p['entry'] * 100
                closed.append((sym, '??', pnl))
                del positions[sym]
        else:
            if price >= p['sl']:
                pnl = (p['entry'] - price) / p['entry'] * 100
                closed.append((sym, '??', pnl))
                del positions[sym]
            elif price <= p['tp']:
                pnl = (p['entry'] - price) / p['entry'] * 100
                closed.append((sym, '??', pnl))
                del positions[sym]

    while len(positions) > MAX_POS:
        positions.pop(list(positions.keys())[0])

    state['positions'] = positions
    state['trades'] = state.get('trades', 0) + new_trades + len(closed)
    total_pnl = state.get('pnl', 0)
    for _, _, pnl in closed: total_pnl += pnl
    state['pnl'] = total_pnl

    # ??????
    if alerts or closed:
        t = now.strftime('%m/%d %H:%M')
        report = []
        report.append('━' * 24)
        report.append('  🎯 妖币扫描v14 | ' + t)
        report.append('━' * 24)

        longs = [a for a in alerts if a.startswith('LONG|')]
        shorts = [a for a in alerts if a.startswith('SHORT|')]

        if longs:
            report.append('  🟢 做多信号')
            for a in longs[:5]:
                parts = a.split('|')
                if len(parts) >= 6:
                    nm = parts[0]
                    sc = parts[1]
                    cv = parts[2]
                    rs = parts[3]
                    pr = parts[4]
                    fl = parts[5] if len(parts) >= 7 else ''
                    cn = nm.replace('USDT', '')
                    ft = ' ⚡闪触' if fl == 'FLASH' else ''
                    report.append('    {:<6} {:>3}分 CVD{:>6}% RSI{:>3} ${}{}'.format(cn, sc, cv, rs, pr, ft))

        if shorts:
            report.append('  🔴 做空信号')
            for a in shorts[:5]:
                parts = a.split('|')
                if len(parts) >= 6:
                    nm = parts[0]
                    sc = parts[1]
                    cv = parts[2]
                    rs = parts[3]
                    pr = parts[4]
                    fl = parts[5] if len(parts) >= 7 else ''
                    cn = nm.replace('USDT', '')
                    ft = ' ⚡闪触' if fl == 'FLASH' else ''
                    report.append('    {:<6} {:>3}分 CVD{:>6}% RSI{:>3} ${}{}'.format(cn, sc, cv, rs, pr, ft))

        if closed:
            report.append('  📋 平仓')
            for sym, reason, pnl in closed:
                em = '✅' if pnl > 0 else '❌'
                cn = sym.replace('USDT', '')
                report.append('    {} {:<6} {} 盈亏:{:+.1f}%'.format(em, cn, reason, pnl))

        pos_list = []
        for sym, p in list(positions.items()):
            cn = sym.replace('USDT', '')
            d = '多' if p['direction'] == 'long' else '空'
            pos_list.append('{}{}'.format(d, cn))
        pos_str = ' '.join(pos_list[:8]) if pos_list else '空仓'

        pnl_emoji = '📈' if total_pnl >= 0 else '📉'
        report.append('  ━' * 16)
        report.append('  持仓: {}/{} | {} 盈亏:{:+.1f}% | 交易:{}笔'.format(len(positions), MAX_POS, pnl_emoji, total_pnl, state['trades']))
        report.append('  [{}]'.format(pos_str))
        report.append('━' * 24)

        feishu_app_send('
'.join(report))

    save_state(state)
    elapsed = time.time() - t0
    flash_count = sum(1 for s in signals if s.get('flash'))
    print('[{}] 候选:{} 信号:{} 闪触:{} 开:{} 平:{} [{:.1f}s]'.format(now.strftime('%H:%M:%S'), len(candidates), len(signals), flash_count, new_trades, len(closed), elapsed))

if __name__ == '__main__':
    print('妖币扫描器 v14 - 实时动量+闪触发 | {}'.format(datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')))
    feishu_send('🔍 妖币扫描器v14上线 | 5m动量候选+orderbook闪触发 | 领先指标驱动')
    while True:
        try:
            scan()
        except Exception as e:
            import traceback
            print('错误: {}'.format(e))
            traceback.print_exc()
        time.sleep(5)
