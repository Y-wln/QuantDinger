"""
Hermes Signal Backtest Bridge V1
=================================
Verifies Hermes/MerCu signal accuracy using forward returns analysis.
Lightweight - does not require the full QuantDinger backtest engine.

For each signal:
1. Fetch kline data before/after signal timestamp
2. Calculate forward returns at 5m, 15m, 1h, 4h, 24h horizons
3. Score: correct direction + magnitude vs threshold
4. Output: accuracy, win rate, avg return, confusion matrix
"""
from __future__ import annotations

import os
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import defaultdict

import pandas as pd
import numpy as np

from app.utils.logger import get_logger

logger = get_logger(__name__)
BJT = timezone(timedelta(hours=8))

# ============================================================
# Configuration
# ============================================================

HORIZONS = {
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "24h": timedelta(hours=24),
}

MIN_RETURN_THRESHOLD = float(os.getenv("HERMES_BACKTEST_MIN_RETURN", "0.003"))  # 0.3% minimum
SIGNIFICANT_RETURN = float(os.getenv("HERMES_BACKTEST_SIG_RETURN", "0.01"))     # 1.0% significant


@dataclass
class SignalBacktestResult:
    """Backtest result for a single signal."""
    symbol: str
    direction: str          # LONG / SHORT
    score: int
    stage: str
    signal_time: datetime
    signal_price: float
    forward_returns: Dict[str, float] = field(default_factory=dict)
    correct: Dict[str, bool] = field(default_factory=dict)
    significant: Dict[str, bool] = field(default_factory=dict)


@dataclass
class AggregateBacktestReport:
    """Aggregate backtest report."""
    total_signals: int = 0
    long_signals: int = 0
    short_signals: int = 0
    horizon_accuracy: Dict[str, float] = field(default_factory=dict)
    horizon_avg_return: Dict[str, float] = field(default_factory=dict)
    horizon_win_rate: Dict[str, float] = field(default_factory=dict)
    horizon_sharpe_approx: Dict[str, float] = field(default_factory=dict)
    by_score_range: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_stage: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_coin_type: Dict[str, Dict[str, float]] = field(default_factory=dict)
    individual_results: List[dict] = field(default_factory=list)


class HermesBacktestBridge:
    """Bridge between Hermes signals and backtest verification."""

    def __init__(self):
        self._kline_cache: Dict[str, pd.DataFrame] = {}

    def _fetch_klines(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1m",
    ) -> pd.DataFrame:
        """Fetch kline data from QuantDinger data sources."""
        cache_key = f"{symbol}:{interval}:{start.isoformat()}:{end.isoformat()}"
        if cache_key in self._kline_cache:
            return self._kline_cache[cache_key].copy()

        try:
            from app.data_sources import DataSourceFactory

            # Convert datetime to unix timestamps
            start_ts = int(start.timestamp() * 1000)
            end_ts = int(end.timestamp() * 1000)

            # Calculate approximate limit based on interval
            interval_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
            minutes = interval_minutes.get(interval, 1)
            total_minutes = (end - start).total_seconds() / 60
            limit = min(int(total_minutes / minutes) + 10, 1500)

            klines = DataSourceFactory.get_kline(
                market="crypto",
                symbol=symbol,
                timeframe=interval,
                limit=limit,
                before_time=end_ts,
                after_time=start_ts,
            )

            if klines and len(klines) > 0:
                df = pd.DataFrame(klines)
                if "time" in df.columns:
                    df["time"] = pd.to_datetime(df["time"], unit="ms")
                self._kline_cache[cache_key] = df.copy()
                return df
        except Exception as e:
            logger.warning(f"Kline fetch failed for {symbol}: {e}")

        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

    def backtest_signal(
        self,
        signal: dict,
    ) -> Optional[SignalBacktestResult]:
        """Backtest a single Hermes signal."""
        symbol = signal.get("symbol", "")
        direction = signal.get("direction", "LONG")
        score = signal.get("score", 0)
        stage = signal.get("stage", "")
        price = signal.get("price", 0)

        if not symbol or not price:
            return None

        # Parse signal time
        ts = signal.get("timestamp", "")
        try:
            if ts:
                signal_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                signal_time = datetime.now(BJT)
        except (ValueError, TypeError):
            signal_time = datetime.now(BJT)

        # Fetch klines: 1h before to 24h after
        start = signal_time - timedelta(hours=1)
        end = signal_time + timedelta(hours=25)
        df = self._fetch_klines(symbol, start, end, "1m")

        if df.empty:
            logger.debug(f"No kline data for {symbol}, skipping backtest")
            return None

        # Find the closest bar to signal time
        if "close_time" in df.columns:
            df["time_delta"] = abs(pd.to_datetime(df["close_time"]) - signal_time)
        elif "open_time" in df.columns:
            df["time_delta"] = abs(pd.to_datetime(df["open_time"]) - signal_time)
        else:
            df["time_delta"] = abs(df.index - signal_time)

        closest_idx = df["time_delta"].idxmin()
        signal_close = float(df.loc[closest_idx, "close"]) if "close" in df.columns else price

        result = SignalBacktestResult(
            symbol=symbol,
            direction=direction,
            score=score,
            stage=stage,
            signal_time=signal_time,
            signal_price=signal_close,
        )

        # Calculate forward returns for each horizon
        signal_ts = pd.to_datetime(df.loc[closest_idx].name if isinstance(df.index, pd.DatetimeIndex)
                                    else df.loc[closest_idx, "close_time" if "close_time" in df.columns else "open_time"])

        for horizon_name, horizon_delta in HORIZONS.items():
            target_time = signal_ts + horizon_delta

            # Find bar closest to target time
            if "close_time" in df.columns:
                future_mask = pd.to_datetime(df["close_time"]) >= target_time
            else:
                future_mask = df.index >= target_time

            if future_mask.any():
                future_idx = future_mask.idxmax()
                future_close = float(df.loc[future_idx, "close"]) if "close" in df.columns else float(df.loc[future_idx].iloc[-1])

                if signal_close > 0:
                    raw_return = (future_close - signal_close) / signal_close
                    if direction == "SHORT":
                        raw_return = -raw_return  # Invert for shorts

                    result.forward_returns[horizon_name] = round(raw_return, 6)
                    result.correct[horizon_name] = raw_return > 0
                    result.significant[horizon_name] = abs(raw_return) >= SIGNIFICANT_RETURN

        return result

    def run_batch(
        self,
        signals: List[dict],
        progress_callback=None,
    ) -> AggregateBacktestReport:
        """Run backtest on a batch of signals."""
        report = AggregateBacktestReport()
        report.total_signals = len(signals)

        horizon_returns: Dict[str, List[float]] = defaultdict(list)
        horizon_correct: Dict[str, List[bool]] = defaultdict(list)

        for i, signal in enumerate(signals):
            direction = signal.get("direction", "LONG")
            if direction == "LONG":
                report.long_signals += 1
            else:
                report.short_signals += 1

            result = self.backtest_signal(signal)
            if result is None:
                continue

            # Collect horizon data
            for h in HORIZONS:
                if h in result.forward_returns:
                    horizon_returns[h].append(result.forward_returns[h])
                    horizon_correct[h].append(result.correct.get(h, False))

            # Store individual result
            report.individual_results.append({
                "symbol": result.symbol,
                "direction": result.direction,
                "score": result.score,
                "stage": result.stage,
                "signal_time": result.signal_time.isoformat(),
                "signal_price": result.signal_price,
                "forward_returns": result.forward_returns,
                "correct": result.correct,
            })

            if progress_callback and i % 10 == 0:
                progress_callback(i, len(signals))

        # Calculate aggregate metrics per horizon
        for h in HORIZONS:
            returns = horizon_returns.get(h, [])
            corrects = horizon_correct.get(h, [])

            if returns:
                report.horizon_avg_return[h] = round(float(np.mean(returns)), 6)
                report.horizon_accuracy[h] = round(
                    sum(1 for c in corrects if c) / len(corrects), 4
                ) if corrects else 0.0
                report.horizon_win_rate[h] = round(
                    sum(1 for r in returns if r > MIN_RETURN_THRESHOLD) / len(returns), 4
                )
                if len(returns) > 1:
                    std = float(np.std(returns))
                    report.horizon_sharpe_approx[h] = round(
                        report.horizon_avg_return[h] / std, 4
                    ) if std > 0 else 0.0

        # Score range breakdown
        score_ranges = [(-50, -20), (-20, -5), (-5, 5), (5, 10), (10, 20), (20, 50)]
        for lo, hi in score_ranges:
            range_signals = [s for s in signals if lo <= s.get("score", 0) < hi]
            if range_signals:
                sub_report = self.run_batch(range_signals)
                key = f"score_{lo}_to_{hi}"
                report.by_score_range[key] = {
                    "count": len(range_signals),
                    "1h_accuracy": sub_report.horizon_accuracy.get("1h", 0),
                    "4h_accuracy": sub_report.horizon_accuracy.get("4h", 0),
                }

        # Stage breakdown
        stage_signals: Dict[str, List[dict]] = defaultdict(list)
        for s in signals:
            stage = s.get("stage", "unknown")
            stage_signals[stage].append(s)
        for stage, sigs in stage_signals.items():
            if len(sigs) >= 3:
                sub_report = self.run_batch(sigs)
                report.by_stage[stage] = {
                    "count": len(sigs),
                    "1h_accuracy": sub_report.horizon_accuracy.get("1h", 0),
                    "4h_accuracy": sub_report.horizon_accuracy.get("4h", 0),
                }

        # Coin type breakdown
        type_signals: Dict[str, List[dict]] = defaultdict(list)
        for s in signals:
            ct = s.get("coin_type", "unknown")
            type_signals[ct].append(s)
        for ct, sigs in type_signals.items():
            if len(sigs) >= 3:
                sub_report = self.run_batch(sigs)
                report.by_coin_type[ct] = {
                    "count": len(sigs),
                    "1h_accuracy": sub_report.horizon_accuracy.get("1h", 0),
                    "4h_accuracy": sub_report.horizon_accuracy.get("4h", 0),
                }

        return report

    def quick_accuracy_report(self, signals: List[dict]) -> str:
        """Generate a human-readable accuracy report."""
        report = self.run_batch(signals)

        lines = []
        lines.append("=" * 60)
        lines.append("  Hermes Signal Accuracy Report")
        lines.append("=" * 60)
        lines.append(f"  Total Signals: {report.total_signals}")
        lines.append(f"  LONG: {report.long_signals}  SHORT: {report.short_signals}")
        lines.append("")
        lines.append("  Horizon Accuracy:")
        lines.append(f"  {'Horizon':<8} {'Accuracy':<10} {'Avg Ret':<10} {'Win Rate':<10} {'Sharpe':<8}")
        lines.append(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
        for h in ["5m", "15m", "1h", "4h", "24h"]:
            acc = report.horizon_accuracy.get(h, 0)
            avg_ret = report.horizon_avg_return.get(h, 0)
            win = report.horizon_win_rate.get(h, 0)
            sharpe = report.horizon_sharpe_approx.get(h, 0)
            lines.append(f"  {h:<8} {acc:<10.1%} {avg_ret:<10.4%} {win:<10.1%} {sharpe:<8.2f}")

        if report.by_score_range:
            lines.append("")
            lines.append("  By Score Range (1h accuracy):")
            for key, val in sorted(report.by_score_range.items()):
                lines.append(f"    {key}: count={val['count']}, acc={val['1h_accuracy']:.1%}")

        lines.append("=" * 60)
        return "\n".join(lines)


# ============================================================
# Singleton
# ============================================================

_bridge: Optional[HermesBacktestBridge] = None


def get_hermes_backtest_bridge() -> HermesBacktestBridge:
    global _bridge
    if _bridge is None:
        _bridge = HermesBacktestBridge()
    return _bridge
