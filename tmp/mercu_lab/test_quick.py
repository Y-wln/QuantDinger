print("Starting...")
from run import MerCuReader, PriceContext, StateTracker, DocumentScorer

r = MerCuReader()
print("Reader OK, fresh:", r.is_fresh())
anomalies = r.get_anomalies()
print("Anomalies:", len(anomalies))
for a in anomalies[:5]:
    print(" ", a.get("sym"), a.get("main_dim_label"), "pct:", a.get("pct_to_ref"), "grade:", a.get("grade"))

# Quick score test
price_ctx = PriceContext()
tracker = StateTracker()
scorer = DocumentScorer(r, price_ctx, tracker)
results = scorer.score_all()
print("\nScored:", len(results))
for r in results[:8]:
    print(f"  {r['symbol']:12s} delta={r['score_delta']:+5.1f} total={r['total_score']:+6.1f} stage={r['stage']} ctx={r['context']}")
    print(f"    reasons: {r['reasons'][:3]}")

signals = scorer.get_signals(min_total=3)
print(f"\nSignals: {len(signals)}")
for s in signals:
    print(f"  {s['direction']:5s} {s['symbol']:12s} score={s['total_score']:+5.1f} stage={s['stage']}")
