import sys
from app.services.hermes_backtest import (
    HermesBacktestBridge, AggregateBacktestReport,
    SignalBacktestResult, get_hermes_backtest_bridge, HORIZONS
)

print("="*50)
print("TEST 3: Backtest Bridge")
print("="*50)

bridge = get_hermes_backtest_bridge()

# 3a. Horizons
assert len(HORIZONS) == 5
print(f"[OK] {len(HORIZONS)} horizons: {list(HORIZONS.keys())}")

# 3b. Report with mock signals
mock = [
    {"symbol": "BTCUSDT", "direction": "LONG", "score": 15, "stage": "main", "price": 64000, "timestamp": "2026-06-18T12:00:00", "coin_type": "INSTITUTIONAL_TREND"},
    {"symbol": "ETHUSDT", "direction": "SHORT", "score": -12, "stage": "distribution", "price": 1680, "timestamp": "2026-06-18T12:00:00", "coin_type": "INSTITUTIONAL_TREND"},
    {"symbol": "BTCUSDT", "direction": "LONG", "score": 8, "stage": "bullish", "price": 64100, "timestamp": "2026-06-18T13:00:00", "coin_type": "INSTITUTIONAL_TREND"},
]

report_txt = bridge.quick_accuracy_report(mock)
assert "Hermes Signal Accuracy Report" in report_txt
assert "Total Signals:" in report_txt
assert "Horizon Accuracy:" in report_txt
print(f"[OK] quick_accuracy_report - valid text report")

# 3c. Batch run
report = bridge.run_batch(mock)
assert isinstance(report, AggregateBacktestReport)
assert report.total_signals == 3
assert report.long_signals == 2
assert report.short_signals == 1
print(f"[OK] run_batch: {report.total_signals} signals ({report.long_signals}L/{report.short_signals}S)")

# 3d. Individual results
print(f"[OK] Individual: {len(report.individual_results)} results")

# 3e-f-g. Breakdowns
print(f"[OK] Score ranges: {len(report.by_score_range)} ranges")
print(f"[OK] Stages: {len(report.by_stage)} stages")
print(f"[OK] Coin types: {len(report.by_coin_type)} types")

# 3h. Horizon metrics structure
for h in HORIZONS:
    assert h in report.horizon_avg_return, f"Missing {h} in horizon_avg_return"
print(f"[OK] All {len(HORIZONS)} horizons have metrics")

print()
print("=== TEST 3 PASSED ===")
