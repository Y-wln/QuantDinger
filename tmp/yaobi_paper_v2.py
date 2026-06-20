import sys, os, json, time, traceback
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from entry_report import entry_report
from hermes_core import feishu_app_send, fetch_fear_greed
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

BJT = timezone(timedelta(hours=8))
DIR = os.path.expanduser('~/trading_logs/yaobi_paper')
os.makedirs(DIR, exist_ok=True)

COINS = [
    'BTCUSDT','ETHUSDT','SOLUSDT','DOGEUSDT','BNBUSDT','XRPUSDT',
    'ADAUSDT','LINKUSDT','AVAXUSDT','DOTUSDT','INJUSDT','TAOUSDT',
    'DASHUSDT','FETUSDT','CHZUSDT','ENAUSDT','LTCUSDT','TONUSDT',
]

def load_state():
    try:
        with open(DIR+'/state.json') as f: return json.load(f)
    except: return {'positions':{}, 'history':[], 'stats':{'trades':0,'wins':0,'total_pnl':0}}

def save_state(s):
    with open(DIR+'/state.json','w') as f: json.dump(s, f, indent=2, default=str)

def run_one(sym):
    state = load_state()
    pos = state['positions']
    name = sym.replace('USDT','')
    
    r = entry_report(sym)
    if not r: return None
    
    sig = r['signal']
    price = r['price']
    entry_ok = r['entry_ok']
    event = None
    
    if name in pos:
        p = pos[name]
        entry = p['entry']
        direction = p['direction']
        sl = p['sl']
        tp = p['tp']
        if direction == 'long':
            pnl = (price - entry) / entry * 100
            if price <= sl:
                state['history'].append({**p, 'exit':price, 'pnl':round(pnl,2), 'reason':'SL'})
                del pos[name]
                state['stats']['trades'] += 1
                if pnl > 0: state['stats']['wins'] += 1
                state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                event = ('CLOSE', name, 'long', round(pnl,2), 'SL')
            elif price >= tp:
                state['history'].append({**p, 'exit':price, 'pnl':round(pnl,2), 'reason':'TP'})
                del pos[name]
                state['stats']['trades'] += 1
                if pnl > 0: state['stats']['wins'] += 1
                state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                event = ('CLOSE', name, 'long', round(pnl,2), 'TP')
        else:
            pnl = (entry - price) / entry * 100
            if price >= sl:
                state['history'].append({**p, 'exit':price, 'pnl':round(pnl,2), 'reason':'SL'})
                del pos[name]
                state['stats']['trades'] += 1
                if pnl > 0: state['stats']['wins'] += 1
                state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                event = ('CLOSE', name, 'short', round(pnl,2), 'SL')
            elif price <= tp:
                state['history'].append({**p, 'exit':price, 'pnl':round(pnl,2), 'reason':'TP'})
                del pos[name]
                state['stats']['trades'] += 1
                if pnl > 0: state['stats']['wins'] += 1
                state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                event = ('CLOSE', name, 'short', round(pnl,2), 'TP')
    elif sig != 'wait' and entry_ok and len(pos) < 10:
        pos[name] = {'direction':sig, 'entry':price, 'sl':r['sl'], 'tp':r['tp'],
            'time':str(datetime.now(BJT)), 'score':r['score']}
        event = ('OPEN', name, sig, price, r['score'])
    
    state['positions'] = pos
    save_state(state)
    return event

if __name__ == '__main__':
    events = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(run_one, sym): sym for sym in COINS}
        for f in as_completed(futures, timeout=90):
            try:
                ev = f.result()
                if ev: events.append(ev)
            except Exception as e:
                print('ERR:', futures[f], e)
    
    state = load_state()
    pos = state['positions']
    stats = state['stats']
    ts = datetime.now(BJT).strftime('%m/%d %H:%M')
    fng = fetch_fear_greed()
    
    lines = ['小鹿模拟盘 @' + ts + ' | ' + str(len(pos)) + '仓 | FnG:' + str(fng)]
    
    for ev in events:
        if ev[0] == 'OPEN':
            d = 'LONG' if ev[2]=='long' else 'SHORT'
            lines.append(d + ' ' + ev[1] + ' @' + str(ev[3]) + ' 评分:' + str(ev[4]))
        elif ev[0] == 'CLOSE':
            pnl_s = ('+' if ev[3]>0 else '') + str(ev[3]) + '%'
            lines.append(ev[4] + ' ' + ev[1] + ' PnL:' + pnl_s)
    
    if pos:
        pl = []
        for n, p in pos.items():
            d = 'L' if p['direction']=='long' else 'S'
            pl.append(d + ':' + n + '@' + str(p['entry']))
        lines.append(' | '.join(pl[:6]))
    
    wr = round(stats['wins']/stats['trades']*100,1) if stats['trades']>0 else 0
    tp_s = ('+' if stats['total_pnl']>0 else '') + str(stats['total_pnl'])
    lines.append(str(stats['trades']) + '笔 WR:' + str(wr) + '% PnL:' + tp_s + '%')
    
    msg = '\n'.join(lines)
    print(msg)
    try:
        feishu_app_send(msg)
    except: pass
