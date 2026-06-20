#!/usr/bin/env python3
'''Yaobi v11 Paper Trading - 用进场分析报告跑模拟盘'''
import sys, os, json, time, traceback
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from entry_report import entry_report
from hermes_core import feishu_app_send, fetch_price as fp, fetch_fear_greed
from datetime import datetime, timezone, timedelta

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
        with open(DIR+'/state.json') as f:
            return json.load(f)
    except: return {'positions':{}, 'history':[], 'stats':{'trades':0,'wins':0,'total_pnl':0}}

def save_state(s):
    with open(DIR+'/state.json','w') as f:
        json.dump(s, f, indent=2, default=str)

def run_one(sym):
    state = load_state()
    pos = state['positions']
    
    r = entry_report(sym)
    if not r: return None
    
    sig = r['signal']
    price = r['price']
    name = r['sym']
    entry_ok = r['entry_ok']
    
    event = None
    
    # Check existing position
    if name in pos:
        p = pos[name]
        entry = p['entry']
        direction = p['direction']
        sl = p['sl']
        tp = p['tp']
        
        if direction == 'long':
            pnl = (price - entry) / entry * 100
            if price <= sl:
                state['history'].append({**p, 'exit':price, 'pnl':round(pnl,2), 'reason':'SL', 'time':str(datetime.now(BJT))})
                del pos[name]
                state['stats']['trades'] += 1
                if pnl > 0: state['stats']['wins'] += 1
                state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                event = ('CLOSE', name, 'long', round(pnl,2), '止损')
            elif price >= tp:
                state['history'].append({**p, 'exit':price, 'pnl':round(pnl,2), 'reason':'TP', 'time':str(datetime.now(BJT))})
                del pos[name]
                state['stats']['trades'] += 1
                if pnl > 0: state['stats']['wins'] += 1
                state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                event = ('CLOSE', name, 'long', round(pnl,2), '止盈')
        else:
            pnl = (entry - price) / entry * 100
            if price >= sl:
                state['history'].append({**p, 'exit':price, 'pnl':round(pnl,2), 'reason':'SL', 'time':str(datetime.now(BJT))})
                del pos[name]
                state['stats']['trades'] += 1
                if pnl > 0: state['stats']['wins'] += 1
                state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                event = ('CLOSE', name, 'short', round(pnl,2), '止损')
            elif price <= tp:
                state['history'].append({**p, 'exit':price, 'pnl':round(pnl,2), 'reason':'TP', 'time':str(datetime.now(BJT))})
                del pos[name]
                state['stats']['trades'] += 1
                if pnl > 0: state['stats']['wins'] += 1
                state['stats']['total_pnl'] = round(state['stats']['total_pnl'] + pnl, 2)
                event = ('CLOSE', name, 'short', round(pnl,2), '止盈')
            # Update trailing stop
            if price < p.get('trail', entry):
                pos[name]['trail'] = price
                pos[name]['sl'] = price + (entry - price) * 0.7  # trail SL
    
    # New position
    elif sig != 'wait' and entry_ok and len(pos) < 8:
        pos[name] = {
            'direction': sig,
            'entry': price,
            'sl': r['sl'],
            'tp': r['tp'],
            'time': str(datetime.now(BJT)),
            'score': r['score'],
            'trail': price,
        }
        event = ('OPEN', name, sig, price, r['score'])
    
    state['positions'] = pos
    save_state(state)
    return event

def run_all():
    events = []
    for sym in COINS:
        try:
            ev = run_one(sym)
            if ev: events.append(ev)
        except Exception as e:
            print(f'  {sym} ERR: {e}')
    return events

if __name__ == '__main__':
    events = run_all()
    state = load_state()
    pos = state['positions']
    stats = state['stats']
    
    ts = datetime.now(BJT).strftime('%m/%d %H:%M')
    fng = fetch_fear_greed()
    
    lines = []
    lines.append('小鹿模拟盘 @' + ts + ' | 持仓:' + str(len(pos)) + ' | FnG:' + str(fng))
    
    if events:
        for ev in events:
            if ev[0] == 'OPEN':
                lines.append(('LONG' if ev[2]=='long' else 'SHORT') + ' ' + ev[1] + ' @' + str(ev[3]) + ' 评分:' + str(ev[4]))
            elif ev[0] == 'CLOSE':
                pnl_str = ('+' if ev[3]>0 else '') + str(ev[3]) + '%'
                lines.append(ev[4] + ' ' + ev[1] + ' PnL:' + pnl_str)
    
    if pos:
        pos_lines = []
        for n, p in pos.items():
            d = 'long' if p['direction']=='long' else 'short'
            pos_lines.append(d + ':' + n + '@' + str(p['entry']))
        lines.append(' | '.join(pos_lines[:5]))
    
    lines.append('累计: ' + str(stats['trades']) + '笔 胜率:' + str(round(stats['wins']/stats['trades']*100,1) if stats['trades']>0 else 0) + '% PnL:' + ('+' if stats['total_pnl']>0 else '') + str(stats['total_pnl']) + '%')
    
    msg = '\n'.join(lines)
    print(msg)
    feishu_app_send(msg)
