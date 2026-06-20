import sys, json, time
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import fetch_klines, fetch_price, ema, rsi, calc_cvd
from urllib.request import Request, build_opener, ProxyHandler

# Get the same proxy setup as yaobi
ph = ProxyHandler({"http":"http://127.0.0.1:7892","https":"http://127.0.0.1:7892"})
opener = build_opener(ph)

# Get 24hr ticker
BINANCE = "https://api.binance.com"
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
print(f"????: {len(candidates)}?")
for sym, vol, chg in candidates[:15]:
    print(f"  {sym}: vol={vol/1e6:.1f}M chg={chg:+.1f}%")

# Now analyze top 5
print("\n=== ???? (top 5) ===")
for sym, vol, chg in candidates[:5]:
    try:
        k1 = fetch_klines(sym, "1h", 100)
        if len(k1) < 50:
            print(f"  {sym}: ????({len(k1)}?)")
            continue
        c = [k["c"] for k in k1]
        rs = rsi(c)
        cv = calc_cvd(k1, 6)
        e20 = ema(c, 20)
        e50 = ema(c, 50)
        price = c[-1]
        trend = "up" if price > e20 > e50 else ("down" if price < e20 < e50 else "neutral")
        score = 0
        # CVD
        if cv > 20: score += 12
        elif cv < -20: score -= 12
        elif cv > 10: score += 6
        elif cv < -10: score -= 6
        # RSI
        if rs < 25: score += 12
        elif rs < 35: score += 6
        elif rs > 75: score -= 12
        elif rs > 65: score -= 6
        # Trend
        if trend == "up": score += 8
        elif trend == "down": score -= 8

        print(f"  {sym}: price={price} CVD={cv:.0f}% RSI={rs:.0f} trend={trend} => score={score}/15")
    except Exception as e:
        print(f"  {sym}: error={e}")
