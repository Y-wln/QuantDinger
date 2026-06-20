import sys, json, time
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import fetch_orderbook_imbalance, fetch_1m_cvd, fetch_tape_pressure, fetch_fear_greed

sym = 'BTCUSDT'
t0 = time.time()
ob = fetch_orderbook_imbalance(sym)
t1 = time.time()
cvd1m = fetch_1m_cvd(sym)
t2 = time.time()
tape = fetch_tape_pressure(sym)
fng = fetch_fear_greed()
t3 = time.time()

print(f"Sym: {sym} FnG: {fng}")
print(f"Orderbook ({t1-t0:.1f}s): {ob}")
print(f"1m CVD ({t2-t1:.1f}s): {cvd1m}%")
print(f"Tape ({t3-t2:.1f}s): {tape}")
