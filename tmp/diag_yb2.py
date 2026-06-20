import sys, json
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines, fetch_price, ema, rsi, calc_cvd, BINANCE
from urllib.request import Request, build_opener, ProxyHandler

ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
opener = build_opener(ph)
data = json.loads(opener.open(Request(BINANCE+"/api/v3/ticker/24hr", headers={"User-Agent":"Mozilla/5.0"}), timeout=15).read())

SKIP = {"BTC","ETH","SOL","BNB","XRP","ADA","DOGE","DOT","LINK","AVAX","LTC","USDC","USDT","DAI","BUSD","TUSD","FDUSD","WBTC","STETH"}
candidates = []
for t in data:
    sym = t.get("symbol","")
    if not sym.endswith("USDT"): continue
    name = sym.replace("USDT","")
    if name in SKIP: continue
    try:
        vol = float(t.get("quoteVolume",0))
        chg = float(t.get("priceChangePercent",0))
        if vol > 3e6 and abs(chg) > 3:
            candidates.append((sym, vol, chg))
    except: pass
candidates.sort(key=lambda x: x[1], reverse=True)

# Direct test of analyze_one logic for top 8
print("=== Direct analyze_one test ===")
for sym, vol, chg in candidates[:8]:
    try:
        k1 = fetch_klines(sym, '1h', 100)
        if len(k1) < 50:
            print(f"  {sym}: insufficient data ({len(k1)})")
            continue
        c = [k['c'] for k in k1]
        rs_arr = rsi(c)
        rs = rs_arr[-1] if isinstance(rs_arr, list) and rs_arr else 50
        cv = calc_cvd(k1, 6)
        e20_arr = ema(c, 20)
        e50_arr = ema(c, 50)
        e20 = (e20_arr[-1] if isinstance(e20_arr, list) and e20_arr else c[-1])
        e50 = (e50_arr[-1] if isinstance(e50_arr, list) and e50_arr else c[-1])
        price = c[-1]
        trend = 'up' if price > e20 > e50 else ('down' if price < e20 < e50 else 'neutral')
        score = 0
        reasons = []
        if cv > 20: score += 12; reasons.append(f'CVD??{int(cv)}%')
        elif cv < -20: score -= 12; reasons.append(f'CVD??{int(cv)}%')
        elif cv > 10: score += 6; reasons.append(f'CVD??{int(cv)}%')
        elif cv < -10: score -= 6; reasons.append(f'CVD??{int(cv)}%')
        if rs < 25: score += 12; reasons.append(f'RSI??{int(rs)}')
        elif rs < 35: score += 6; reasons.append(f'RSI??{int(rs)}')
        elif rs > 75: score -= 12; reasons.append(f'RSI??{int(rs)}')
        elif rs > 65: score -= 6; reasons.append(f'RSI??{int(rs)}')
        if trend == 'up': score += 8; reasons.append('????')
        elif trend == 'down': score -= 8; reasons.append('????')
        sig = 'long' if score >= 12 else ('short' if score <= -12 else 'wait')
        print(f"  {sym}: price={price:.4f} CVD={cv:.0f}% RSI={rs:.0f} trend={trend} score={score} sig={sig} | {' '.join(reasons)}")
    except Exception as e:
        import traceback
        print(f"  {sym}: ERROR {e}")
        traceback.print_exc()
