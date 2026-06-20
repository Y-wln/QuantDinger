"""Hermes Backtest V3 - Signal accuracy verification engine.

Lightweight forward-returns analysis. Uses CoinGecko API for historical prices.
Integrates with SignalTracker to verify accuracy of tracked signals.

Usage:
  from app.services.hermes_strategies.hermes_backtest_v3 import run_batch_backtest
  report = run_batch_backtest(signals, hours_back=24)
"""
from __future__ import annotations
import os, time, json, logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import defaultdict

import requests

logger = logging.getLogger(__name__)
BJT = timezone(timedelta(hours=8))

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_ID_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "DOT": "polkadot",
    "AVAX": "avalanche-2", "LINK": "chainlink", "LTC": "litecoin",
    "INJ": "injective-protocol", "FET": "fetch-ai", "WLD": "worldcoin-wld",
    "APT": "aptos", "ARB": "arbitrum", "OP": "optimism", "SUI": "sui",
    "NEAR": "near", "RNDR": "render-token", "TAO": "bittensor",
    "TIA": "celestia", "SEI": "sei-network", "AAVE": "aave",
    "UNI": "uniswap", "ATOM": "cosmos", "FIL": "filecoin",
    "HBAR": "hedera-hashgraph", "ICP": "internet-computer",
    "TRX": "tron", "SHIB": "shiba-inu", "PEPE": "pepe",
    "COAI": "codex", "HYPE": "hyperliquid", "MEGA": "megabit",
    "ZEC": "zcash", "XLM": "stellar", "ALGO": "algorand",
    "VET": "vechain", "THETA": "theta-token", "FTM": "fantom",
    "EGLD": "elrond-erd-2", "FLOW": "flow", "QNT": "quant-network",
    "IMX": "immutable-x", "STX": "blockstack", "GRT": "the-graph",
    "SAND": "the-sandbox", "MANA": "decentraland", "APE": "apecoin",
    "GALA": "gala", "AXS": "axie-infinity", "ENJ": "enjincoin",
    "CHZ": "chiliz", "BAT": "basic-attention-token", "ZRX": "0x",
    "CRV": "curve-dao-token", "COMP": "compound-governance-token",
    "MKR": "maker", "SNX": "havven", "YFI": "yearn-finance",
    "SUSHI": "sushi", "1INCH": "1inch", "DYDX": "dydx-chain",
    "LDO": "lido-dao", "GMX": "gmx", "GNS": "gains-network",
}

HORIZONS = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "24h": 1440}

_price_cache: Dict[str, Tuple[float, List[dict]]] = {}


@dataclass
class BacktestSignalResult:
    symbol: str
    direction: str
    score: int
    signal_time: str
    signal_price: float
    forward_returns: Dict[str, float] = field(default_factory=dict)
    correct: Dict[str, bool] = field(default_factory=dict)
    error: str = ""


@dataclass
class BacktestReport:
    total: int = 0
    longs: int = 0
    shorts: int = 0
    horizon_accuracy: Dict[str, float] = field(default_factory=dict)
    horizon_avg_return: Dict[str, float] = field(default_factory=dict)
    horizon_win_rate: Dict[str, float] = field(default_factory=dict)
    by_score_range: Dict[str, Dict] = field(default_factory=dict)
    results: List[dict] = field(default_factory=list)


def _cg_id_for_symbol(symbol: str) -> Optional[str]:
    sym = symbol.upper().replace("USDT", "").replace("1000", "").strip()
    if sym in COINGECKO_ID_MAP:
        return COINGECKO_ID_MAP[sym]
    try:
        r = requests.get(f"{COINGECKO_BASE}/search?query={sym.lower()}", timeout=10)
        if r.status_code == 200:
            coins = r.json().get("coins", [])
            if coins:
                COINGECKO_ID_MAP[sym] = coins[0]["id"]
                return coins[0]["id"]
    except Exception:
        pass
    return None


def _fetch_prices(symbol: str, hours_back: int = 24) -> List[Tuple[int, float]]:
    """Fetch 5-minute OHLC prices. Returns [(timestamp_ms, price), ...]."""
    cache_key = f"{symbol}:{hours_back}"
    now = time.time()
    if cache_key in _price_cache:
        cached_time, cached_data = _price_cache[cache_key]
        if now - cached_time < 300:
            return cached_data

    cg_id = _cg_id_for_symbol(symbol)
    if not cg_id:
        return []

    try:
        days = max(1, hours_back // 24 + 2)
        url = f"{COINGECKO_BASE}/coins/{cg_id}/ohlc?vs_currency=usd&days={days}"
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return []
        ohlc = r.json()
        prices = [(int(p[0]), (p[1] + p[4]) / 2) for p in ohlc]
        _price_cache[cache_key] = (now, prices)
        return prices
    except Exception as e:
        logger.warning(f"Coingecko fetch failed for {symbol}: {e}")
        return []


def _price_at(prices: List[Tuple[int, float]], target_ms: int, offset_min: int = 0) -> Optional[float]:
    """Get price at target_ms + offset_min. Nearest match."""
    target = target_ms + offset_min * 60 * 1000
    if not prices:
        return None
    best = min(prices, key=lambda p: abs(p[0] - target))
    if abs(best[0] - target) > 10 * 60 * 1000:
        return None
    return best[1]


def verify_signal(symbol: str, direction: str, signal_time_str: str,
                  signal_price: float = 0) -> BacktestSignalResult:
    """Verify a single signal's accuracy using forward returns."""
    result = BacktestSignalResult(
        symbol=symbol, direction=direction, score=0,
        signal_time=signal_time_str, signal_price=signal_price,
    )

    try:
        ts = datetime.strptime(signal_time_str, "%Y-%m-%d %H:%M:%S")
        signal_ms = int(ts.replace(tzinfo=BJT).timestamp() * 1000)
    except Exception:
        try:
            ts = datetime.fromisoformat(signal_time_str)
            signal_ms = int(ts.timestamp() * 1000)
        except Exception:
            result.error = f"bad timestamp: {signal_time_str}"
            return result

    prices = _fetch_prices(symbol, hours_back=48)
    if not prices:
        result.error = "no_price_data"
        return result

    entry_price = signal_price or _price_at(prices, signal_ms, 0) or 0
    if entry_price <= 0:
        result.error = "no_entry_price"
        return result

    result.signal_price = entry_price

    for horizon_name, offset_min in HORIZONS.items():
        future_price = _price_at(prices, signal_ms, offset_min)
        if future_price is None or future_price <= 0 or entry_price <= 0:
            continue
        ret = (future_price - entry_price) / entry_price
        result.forward_returns[horizon_name] = round(ret * 100, 2)
        if direction == "LONG":
            result.correct[horizon_name] = ret > 0
        else:
            result.correct[horizon_name] = ret < 0

    return result


def run_batch_backtest(signals: List[dict], hours_back: int = 24,
                        progress_callback=None) -> BacktestReport:
    """Run backtest on a batch of signals. Returns aggregate report."""
    report = BacktestReport()
    results = []
    total = len(signals)

    for i, sig in enumerate(signals):
        symbol = sig.get("symbol", "")
        direction = sig.get("direction", "LONG")
        signal_time = sig.get("timestamp", sig.get("signal_time", ""))
        price = sig.get("price", sig.get("signal_price", 0))
        score = sig.get("score", 0)

        if not symbol or not signal_time:
            continue

        r = verify_signal(symbol, direction, signal_time, price)
        results.append(r)

        if direction == "LONG":
            report.longs += 1
        else:
            report.shorts += 1

        if progress_callback and i % 10 == 0:
            progress_callback(i, total)

    report.total = len(results)

    # Aggregate by horizon
    for h in HORIZONS:
        correct = [r for r in results if h in r.correct and not r.error]
        if correct:
            acc = sum(1 for r in correct if r.correct[h]) / len(correct)
            report.horizon_accuracy[h] = round(acc * 100, 1)
            rets = [r.forward_returns[h] for r in correct if h in r.forward_returns]
            if rets:
                report.horizon_avg_return[h] = round(sum(rets) / len(rets), 2)
                wins = sum(1 for r in correct if r.correct[h])
                report.horizon_win_rate[h] = round(wins / len(correct) * 100, 1)

    # By score range
    ranges = {"high": (20, 99), "mid": (10, 19), "low": (5, 9), "weak": (-99, 4)}
    for rname, (lo, hi) in ranges.items():
        in_range = [r for r in results if lo <= sig_score(r, signals) <= hi]
        if in_range:
            correct_1h = sum(1 for r in in_range if r.correct.get("1h", False))
            report.by_score_range[rname] = {
                "count": len(in_range),
                "accuracy_1h": round(correct_1h / len(in_range) * 100, 1) if in_range else 0,
            }

    report.results = [
        {
            "symbol": r.symbol, "direction": r.direction,
            "signal_time": r.signal_time, "signal_price": r.signal_price,
            "forward_returns": r.forward_returns,
            "correct": r.correct, "error": r.error,
        }
        for r in results
    ]

    return report


def sig_score(result: BacktestSignalResult, signals: List[dict]) -> int:
    for s in signals:
        if s.get("symbol") == result.symbol:
            return abs(s.get("score", 0))
    return 0


def quick_accuracy_report(signals: List[dict]) -> dict:
    """Quick accuracy summary without full backtest."""
    report = run_batch_backtest(signals)
    return {
        "total": report.total,
        "longs": report.longs,
        "shorts": report.shorts,
        "accuracy_1h": report.horizon_accuracy.get("1h", 0),
        "accuracy_4h": report.horizon_accuracy.get("4h", 0),
        "avg_return_1h": report.horizon_avg_return.get("1h", 0),
        "win_rate_1h": report.horizon_win_rate.get("1h", 0),
        "score_ranges": report.by_score_range,
    }
