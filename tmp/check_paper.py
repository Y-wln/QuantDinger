import json
with open('/home/ubuntu/trading_logs/yaobi_paper/state.json') as f:
    s = json.load(f)
pos = s['positions']
print('持仓:', len(pos))
for n, p in pos.items():
    print(' ', n, p['direction'], '@', p['entry'], '评分:', p['score'])
st = s['stats']
wr = round(st['wins']/st['trades']*100,1) if st['trades']>0 else 0
print('交易:', st['trades'], '笔 胜率:', wr, '% PnL:', st['total_pnl'], '%')
