import sys, os, json, time
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

def analyze_only(sym):
    '''Worker: only analyze, no state changes'''
    r = entry_report(sym)
    if not r: return None
    return r

if __name__ == '__main__':
    # Phase 1: parallel analysis
    analyses = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(analyze_only, sym): sym for sym in COINS}
        for f in as_completed(futures, timeout=90):
            sym = futures[f]
            try:
                r = f.result()
                if r: analyses[sym] = r
            except Exception as e:
                print('ERR:', sym, e)
    
    # Phase 2: single-threaded position management
    state = load_state()
    pos = state['positions']
    events = []
    MAX_POS = 8
    
    for sym, r in analyses.items():
        name = r['sym']
        sig = r['signal']
        price = r['price']
        entry_ok = r['entry_ok']
        
        if name in pos:
            p = pos[name]
            entry = p['entry']
            d = p['direction']
            sl = p['sl']
            tp = p['tp']
            if d == 'long':
                pnl = (price - entry) / entry * 100
                if price <= sl or price >= tp:
                    pos.pop(name)
                    state['stats']['trades'] += 1
                    if pnl > 0: state['stats']['wins'] += 1
                    state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                    reason = 'TP' if price >= tp else 'SL'
                    events.append(('CLOSE', name, d, round(pnl,2), reason))
            else:
                pnl = (entry - price) / entry * 100
                if price >= sl or price <= tp:
                    pos.pop(name)
                    state['stats']['trades'] += 1
                    if pnl > 0: state['stats']['wins'] += 1
                    state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                    reason = 'TP' if price <= tp else 'SL'
                    events.append(('CLOSE', name, d, round(pnl,2), reason))
        elif sig != 'wait' and entry_ok and len(pos) < MAX_POS:
            pos[name] = {'direction':sig, 'entry':price, 'sl':r['sl'], 'tp':r['tp'],
                'score':r['score'], 'time':str(datetime.now(BJT))}
            events.append(('OPEN', name, sig, price, r['score']))
    
    save_state(state)
    
    # Report
    ts = datetime.now(BJT).strftime('%m/%d %H:%M')
    fng = fetch_fear_greed()
    lines = ['小鹿模拟盘 @' + ts + ' | ' + str(len(pos)) + '仓 | FnG:' + str(fng)]
    
    for ev in events:
        if ev[0] == 'OPEN':
            lines.append(('LONG' if ev[2]=='long' else 'SHORT') + ' ' + ev[1] + ' @' + str(ev[3]) + ' 评分:' + str(ev[4]))
        elif ev[0] == 'CLOSE':
            lines.append(ev[4] + ' ' + ev[1] + ' PnL:' + ('+' if ev[3]>0 else '') + str(ev[3]) + '%')
    
    if pos:
        pl = []
        for n, p in pos.items():
            pl.append(('L' if p['direction']=='long' else 'S') + ':' + n)
        lines.append(' | '.join(pl[:6]))
    
    stats = state['stats']
    wr = round(stats['wins']/stats['trades']*100,1) if stats['trades']>0 else 0
    tp_s = ('+' if stats['total_pnl']>0 else '') + str(stats['total_pnl'])
    lines.append(str(stats['trades']) + '笔 WR:' + str(wr) + '% PnL:' + tp_s + '%')
    
    msg = '\n'.join(lines)
    print(msg)
    try: feishu_app_send(msg)
    except: pass
