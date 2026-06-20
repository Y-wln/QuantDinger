import sys, json, time
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import fetch_klines, fetch_price, fetch_fear_greed
from agent_technical import TechnicalAgent

ta = TechnicalAgent()
sym = 'ETHUSDT'
k4 = fetch_klines(sym, '4h', 300)
k1 = fetch_klines(sym, '1h', 300)
k5 = fetch_klines(sym, '5m', 50)
k15 = fetch_klines(sym, '15m', 30)
fng = fetch_fear_greed()
price = fetch_price(sym)

r = ta.analyze(k4, k1, k5, k15, sym, fng=fng)
print(f"=== {sym} ===")
print(f"  Price: {price}")
print(f"  Score: {r.get('score',0)}")
print(f"  Signal: {r.get('signal','?')}")
print(f"  FnG: {fng}")
print(f"  Details: {json.dumps(r.get('details',{}), ensure_ascii=False, indent=2)}")
print(f"  Leading: {r.get('leading_signals',[])}")
