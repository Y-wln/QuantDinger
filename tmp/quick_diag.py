import sys, json, time
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import fetch_klines, fetch_price, fetch_fear_greed
from agent_technical import TechnicalAgent
from concurrent.futures import ThreadPoolExecutor, as_completed

ta = TechnicalAgent()
fng = fetch_fear_greed()
coins = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','DOGEUSDT']

def analyze_one(sym):
    k4 = fetch_klines(sym, '4h', 300)
    k1 = fetch_klines(sym, '1h', 300)
    k5 = fetch_klines(sym, '5m', 50)
    k15 = fetch_klines(sym, '15m', 30)
    if len(k4) < 50:
        return (sym, None)
    r = ta.analyze(k4, k1, k5, k15, sym, fng=fng)
    return (sym, r)

with ThreadPoolExecutor(max_workers=4) as ex:
    futures = {ex.submit(analyze_one, s): s for s in coins}
    for f in as_completed(futures, timeout=45):
        try:
            sym, r = f.result()
            if r:
                p = fetch_price(sym)
                print(f"{sym.replace('USDT',''):6s} ${p:<10.4f} score={r['score']:4d} signal={r['signal']:6s} leads={r.get('leading_signals',[])[:3]}")
        except Exception as e:
            print(f"{futures[f]}: error={e}")
