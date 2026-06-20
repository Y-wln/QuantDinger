import sys, json
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import (fetch_klines, fetch_price, fetch_fear_greed, fetch_oi_history,
    fetch_taker_volume, fetch_long_short_ratio, fetch_funding_rate,
    fetch_orderbook_imbalance, fetch_1m_cvd, fetch_tape_pressure)
from agent_technical import TechnicalAgent

ta = TechnicalAgent()
sym = 'BTCUSDT'
k4 = fetch_klines(sym, '4h', 300)
k1 = fetch_klines(sym, '1h', 300)
k5 = fetch_klines(sym, '5m', 50)
k15 = fetch_klines(sym, '15m', 30)
fng = fetch_fear_greed()
price = fetch_price(sym)

r = ta.analyze(k4, k1, k5, k15, sym, fng=fng)

# Now test leading signals
print(f"=== {sym} Technical Only ===")
print(f"  Score: {r['score']}, Signal: {r['signal']}")
print(f"  Leads: {r.get('leading_signals',[])[:4]}")

# Test order book
ob = fetch_orderbook_imbalance(sym)
if ob:
    print(f"\n  Orderbook imbalance: {ob['imbalance']}% bid:{ob['bid_vol']:.0f} ask:{ob['ask_vol']:.0f}")

# Test 1m CVD
cvd1m = fetch_1m_cvd(sym)
print(f"  1m CVD: {cvd1m}%")

# Test tape pressure
tape = fetch_tape_pressure(sym)
if tape:
    print(f"  Tape: {tape['pressure']} buy_ratio:{tape['buy_ratio']} large_net:{tape['large_net']}")

# Test OI
oi_hist = fetch_oi_history(sym, '5m', 5)
if oi_hist and len(oi_hist) >= 4:
    oi_change = (oi_hist[-1] - oi_hist[0]) / oi_hist[0] * 100 if oi_hist[0] > 0 else 0
    print(f"  OI 5m change: {oi_change:.1f}%")

# Taker
taker = fetch_taker_volume(sym)
print(f"  Taker: ratio={taker.get('ratio',0.5):.2f} trend={taker.get('trend','?')}")

# LSR
lsr = fetch_long_short_ratio(sym)
print(f"  LSR: {lsr:.2f}")

# Funding
fr = fetch_funding_rate(sym)
print(f"  Funding rate: {fr*100:.4f}%")
