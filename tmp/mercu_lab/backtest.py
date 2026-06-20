"""mercu-lab backtest: test signal accuracy against real price data."""
import json, os, sys, time
from datetime import datetime, timezone, timedelta
from run import MerCuReader, PriceContext, StateTracker, DocumentScorer

BJT = timezone(timedelta(hours=8))

def backtest(reader, scorer, lookback_minutes=120):
    """Run backtest: score all anomalies, then check price outcomes."""
    print(f"Backtest: scoring all current anomalies...")
    results = scorer.score_all()
    signals = scorer.get_signals(min_total=3)

    if not signals:
        print("No signals to test.")
        return

    print(f"\n{len(signals)} signals to test:")
    for s in signals:
        print(f"  {s['direction']:5s} {s['symbol']:12s} score={s['total_score']:+5.1f} stage={s['stage']} events={s['events']}")

    # Fetch prices
    print(f"\nFetching prices from Binance...")
    sys.path.insert(0, "/home/ubuntu/hermes-v2")
    from core.http_client import HTTPClient
    from core.exchange import ExchangeAPI

    http = HTTPClient()
    ex = ExchangeAPI(http)

    results_accuracy = {"long": {"win": 0, "loss": 0}, "short": {"win": 0, "loss": 0}}

    for s in signals:
        try:
            sym = s["symbol"]
            direction = s["direction"]
            klines = ex.klines(sym, "1m", 90)

            if not klines or len(klines) < 20:
                print(f"  {sym}: no kline data")
                continue

            # Current price
            current = float(klines[-1]["c"])

            # Prices at 5, 15, 30 min ago (approximately)
            for offset, label in [(15, "15min"), (5, "5min")]:
                if len(klines) > offset:
                    past = float(klines[-offset]["c"])
                    pct = (current - past) / past * 100

                    if direction == "long" and pct > 0.3:
                        results_accuracy["long"]["win"] += 1
                    elif direction == "long" and pct < -0.3:
                        results_accuracy["long"]["loss"] += 1
                    elif direction == "short" and pct < -0.3:
                        results_accuracy["short"]["win"] += 1
                    elif direction == "short" and pct > 0.3:
                        results_accuracy["short"]["loss"] += 1

            print(f"  {sym:12s} current=${current} dir={direction}")

        except Exception as e:
            print(f"  {sym}: error {e}")

    print(f"\n=== Accuracy ===")
    for d in ("long", "short"):
        r = results_accuracy[d]
        total = r["win"] + r["loss"]
        if total > 0:
            print(f"  {d:5s}: {r['win']}W/{r['loss']}L = {100*r['win']/total:.0f}%")


if __name__ == "__main__":
    reader = MerCuReader()
    price_ctx = PriceContext()
    tracker = StateTracker()
    scorer = DocumentScorer(reader, price_ctx, tracker)

    print(f"Data fresh: {reader.is_fresh()}")
    backtest(reader, scorer)
