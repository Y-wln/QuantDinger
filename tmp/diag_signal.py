import sys, json
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import fetch_klines, fetch_price, fetch_fear_greed, fetch_oi, fetch_taker_volume, fetch_long_short_ratio, fetch_funding_rate, ema, rsi, macd, supertrend, calc_cvd, detect_structure, bollinger_bands, detect_launch
from agent_technical import TechnicalAgent

ta = TechnicalAgent()

for sym in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
    k4 = fetch_klines(sym, '4h', 300)
    k1 = fetch_klines(sym, '1h', 300)
    k5 = fetch_klines(sym, '5m', 50)
    k15 = fetch_klines(sym, '15m', 30)
    fng = fetch_fear_greed()
    price = fetch_price(sym)
    
    r = ta.analyze(k4, k1, k5, k15, sym, fng=fng)
    print(f"\n=== {sym} ===")
    print(f"  Price: {price}")
    print(f"  Score: {r.get('score',0)}")
    print(f"  Signal: {r.get('signal','?')}")
    print(f"  FnG: {fng}")
    print(f"  Details: {json.dumps(r.get('details',{}), ensure_ascii=False)}")
    print(f"  Leading: {r.get('leading_signals',[])}")
