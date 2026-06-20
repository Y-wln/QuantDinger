import json
with open("/home/ubuntu/scripts/backtest_v30_20.json") as f:
    d = json.load(f)

results = d.get("results", [])
print("=== ?????BTC?????????? ===\n")
print(f"{'??':<8} {'?PnL':>7} {'??PnL':>8} {'??PnL':>8} {'???':>6}")
print("-" * 42)
for r in sorted(results, key=lambda x: x.get("total_pnl",0), reverse=True):
    sym = r["symbol"].replace("USDT","")
    total = r.get("total_pnl", 0)
    trades = r.get("trades", 0)
    longs = r.get("longs", 0)
    shorts = r.get("shorts", 0)
    # Estimate long/short PnL from backtest
    print(f"{sym:<8} {total:>+6.1f}% {trades:>3}? {longs:>2}?/{shorts:>2}?")

print("\n???BTC????????????")
print("?APT/ADA/DOGE?????????BTC?????")
