"""Hermes Backtest Runner V1 - Complete signal validation pipeline."""
from __future__ import annotations
import os, sys, json, time, logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import defaultdict
import requests, numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hermes_backtest_runner")
BJT = timezone(timedelta(hours=8))

HORIZONS = {"5m": 5, "15m": 15, "1h": 60, "4h": 240}
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_ID_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "DOT": "polkadot",
    "AVAX": "avalanche-2", "LINK": "chainlink", "LTC": "litecoin",
    "INJ": "injective-protocol", "FET": "fetch-ai", "WLD": "worldcoin-wld",
    "APT": "aptos", "ARB": "arbitrum", "OP": "optimism", "SUI": "sui",
    "NEAR": "near", "RNDR": "render-token", "TAO": "bittensor",
    "TIA": "celestia", "SEI": "sei-network",
}

class CoinGeckoKlineFetcher:
    def __init__(self):
        self._cache: Dict[str, List[dict]] = {}
    def _id_for_symbol(self, symbol: str) -> Optional[str]:
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
        except: pass
        return None
    def fetch_5min_prices(self, symbol: str, hours_back: int = 24) -> List[dict]:
        cache_key = f"{symbol}:{hours_back}"
        if cache_key in self._cache: return self._cache[cache_key]
        cg_id = self._id_for_symbol(symbol)
        if not cg_id: return []
        try:
            days = max(1, hours_back // 24 + 1)
            r = requests.get(f"{COINGECKO_BASE}/coins/{cg_id}/market_chart", params={"vs_currency": "usd", "days": days}, timeout=15)
            if r.status_code != 200: return []
            prices = r.json().get("prices", [])
            result = [{"time": int(p[0]), "price": p[1]} for p in prices]
            self._cache[cache_key] = result
            return result
        except Exception as e:
            logger.error(f"CoinGecko fetch error {symbol}: {e}")
            return []
    def price_at(self, prices: List[dict], ts_ms: int) -> Optional[float]:
        if not prices: return None
        best, best_diff = None, float("inf")
        for p in prices:
            diff = abs(p["time"] - ts_ms)
            if diff < best_diff: best_diff = diff; best = p["price"]
        return best
    def forward_return(self, prices: List[dict], from_ts_ms: int, minutes: int) -> Optional[float]:
        entry = self.price_at(prices, from_ts_ms)
        exit_px = self.price_at(prices, from_ts_ms + minutes * 60000)
        if entry and exit_px and entry > 0: return (exit_px - entry) / entry
        return None

class SignalGenerator:
    def __init__(self):
        self.strategies = []; self._init()
    def _init(self):
        try:
            from app.services.hermes_strategies import get_all_strategies, get_dag
            self.strategies = get_all_strategies(); self.dag = get_dag()
            logger.info(f"Loaded {len(self.strategies)} strategies")
        except Exception as e:
            logger.warning(f"Strategy import failed: {e}")
            self.strategies = []; self.dag = None
    def fetch_mercu_data(self) -> dict:
        try:
            r = requests.get("http://124.221.104.66:5000/api/hermes/mercu/raw", timeout=10)
            if r.status_code == 200: return r.json()
        except: pass
        return {"anomalies": [], "momentum": {"boards": {}}}
    def generate_signals(self, mercu_data: dict) -> List[dict]:
        all_signals = []
        for strat in self.strategies:
            try:
                for s in strat.generate(mercu_data):
                    all_signals.append({
                        "symbol": s.symbol, "direction": s.direction,
                        "score": s.score, "price": getattr(s, "price", 0.0),
                        "stage": getattr(s, "stage", ""),
                        "source": getattr(s, "source", strat.name),
                        "confidence": getattr(s, "confidence", "medium"),
                        "timestamp": datetime.now(BJT).isoformat(),
                        "timestamp_ms": int(time.time() * 1000),
                    })
            except Exception as e:
                logger.error(f"Strategy {strat.name}: {e}")
        return all_signals

@dataclass
class BacktestReport:
    total: int = 0; long_count: int = 0; short_count: int = 0
    by_horizon: Dict[str, dict] = field(default_factory=dict)
    by_strategy: Dict[str, dict] = field(default_factory=dict)
    by_direction: Dict[str, dict] = field(default_factory=dict)
    details: List[dict] = field(default_factory=list)

class BacktestVerifier:
    def __init__(self):
        self.kline = CoinGeckoKlineFetcher()
    def verify_signal(self, sig: dict) -> Optional[dict]:
        symbol = sig.get("symbol", ""); direction = sig.get("direction", "NEUTRAL")
        ts_ms = sig.get("timestamp_ms", 0)
        if not symbol or direction == "NEUTRAL" or not ts_ms: return None
        prices = self.kline.fetch_5min_prices(symbol)
        if not prices or len(prices) < 10: return None
        result = {"symbol": symbol, "direction": direction, "score": sig.get("score", 0),
                  "source": sig.get("source", ""), "returns": {}, "correct": {}}
        for h_name, h_mins in HORIZONS.items():
            ret = self.kline.forward_return(prices, ts_ms, h_mins)
            result["returns"][h_name] = ret
            if ret is not None:
                result["correct"][h_name] = ret > 0.003 if direction == "LONG" else ret < -0.003
            else:
                result["correct"][h_name] = False
        return result
    def run(self, signals: List[dict]) -> BacktestReport:
        report = BacktestReport(total=len(signals))
        h_rets = defaultdict(list); h_correct = defaultdict(list)
        s_correct = defaultdict(lambda: defaultdict(list))
        d_correct = defaultdict(lambda: defaultdict(list))
        for i, sig in enumerate(signals):
            logger.info(f"[{i+1}/{len(signals)}] {sig['symbol']} {sig['direction']} score={sig['score']}")
            r = self.verify_signal(sig)
            if not r: continue
            if sig["direction"] == "LONG": report.long_count += 1
            else: report.short_count += 1
            detail = {"symbol": r["symbol"], "direction": r["direction"], "score": r["score"], "source": r["source"]}
            for h_name in HORIZONS:
                ret = r["returns"].get(h_name)
                if ret is not None:
                    h_rets[h_name].append(ret)
                    h_correct[h_name].append(r["correct"][h_name])
                    detail[f"ret_{h_name}"] = round(ret, 5)
                    detail[f"ok_{h_name}"] = r["correct"][h_name]
                s_correct[r["source"]][h_name].append(r["correct"].get(h_name, False))
                d_correct[r["direction"]][h_name].append(r["correct"].get(h_name, False))
            report.details.append(detail)
            time.sleep(1.5)
        for h_name in HORIZONS:
            rets = h_rets.get(h_name, []); corrects = h_correct.get(h_name, [])
            if rets:
                report.by_horizon[h_name] = {
                    "count": len(rets),
                    "accuracy": round(sum(1 for c in corrects if c) / len(corrects), 4),
                    "avg_return": round(float(np.mean(rets)), 5),
                    "median_return": round(float(np.median(rets)), 5),
                }
        for src, hd in s_correct.items():
            report.by_strategy[src] = {}
            for h_name, corrects in hd.items():
                if corrects:
                    report.by_strategy[src][h_name] = round(sum(1 for c in corrects if c) / len(corrects), 4)
        for dn, hd in d_correct.items():
            report.by_direction[dn] = {}
            for h_name, corrects in hd.items():
                if corrects:
                    report.by_direction[dn][h_name] = round(sum(1 for c in corrects if c) / len(corrects), 4)
        return report

def format_report(report: BacktestReport) -> str:
    lines = ["=" * 65, "  Hermes Signal Backtest Accuracy Report", "=" * 65,
             f"  Total: {report.total}  LONG:{report.long_count}  SHORT:{report.short_count}", ""]
    if report.by_horizon:
        lines.append("  Horizon Accuracy:")
        lines.append(f"  {'Horizon':<8} {'Count':<6} {'Accuracy':<10} {'AvgRet':<10} {'MedRet':<10}")
        lines.append(f"  {'-'*8} {'-'*6} {'-'*10} {'-'*10} {'-'*10}")
        for h in ["5m", "15m", "1h", "4h"]:
            d = report.by_horizon.get(h)
            if d:
                lines.append(f"  {h:<8} {d['count']:<6} {d['accuracy']:<10.1%} {d['avg_return']:<10.3%} {d['median_return']:<10.3%}")
    if report.by_strategy:
        lines.append(""); lines.append("  Strategy Accuracy:")
        for src, hd in sorted(report.by_strategy.items()):
            accs = " | ".join(f"{h}:{acc:.1%}" for h, acc in sorted(hd.items()))
            lines.append(f"    {src}: {accs}")
    if report.by_direction:
        lines.append(""); lines.append("  Direction Accuracy:")
        for dn, hd in report.by_direction.items():
            accs = " | ".join(f"{h}:{acc:.1%}" for h, acc in sorted(hd.items()))
            lines.append(f"    {dn}: {accs}")
    if report.details:
        lines.append(""); lines.append("  Recent Signals (top 10):")
        for d in report.details[:10]:
            accs = []
            for h in ["5m","15m","1h"]:
                ok = d.get(f"ok_{h}"); accs.append(f"{h}:{'OK' if ok else 'NO'}" if ok is not None else f"{h}:--")
            lines.append(f"    {d['symbol']:<8} {d['direction']:<6} s={d['score']:>4}  {' | '.join(accs)}")
    lines.append(""); lines.append("=" * 65)
    return "\n".join(lines)

def run_backtest(use_historical: bool = True) -> BacktestReport:
    gen = SignalGenerator(); ver = BacktestVerifier()
    logger.info("Fetching MerCu data...")
    data = gen.fetch_mercu_data()
    logger.info(f"Anomalies: {len(data.get('anomalies',[]))}")
    signals = gen.generate_signals(data)
    logger.info(f"Generated {len(signals)} signals")
    if not signals: return BacktestReport(total=0)
    if use_historical:
        now_ms = int(time.time() * 1000)
        shifts = [240, 180, 120, 60]
        for i, sig in enumerate(signals):
            shift = shifts[i % len(shifts)]
            sig["timestamp_ms"] = now_ms - shift * 60000
            sig["timestamp"] = datetime.fromtimestamp(sig["timestamp_ms"] / 1000, BJT).isoformat()
        logger.info("Shifted signals back for historical verification")
    return ver.run(signals)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true"); p.add_argument("--json", action="store_true")
    p.add_argument("--save", type=str)
    args = p.parse_args()
    print(f"Hermes Backtest Runner | {datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')} BJT\n")
    if args.live:
        gen = SignalGenerator(); data = gen.fetch_mercu_data()
        sigs = gen.generate_signals(data)
        sp = args.save or "hermes_signals_snapshot.json"
        with open(sp, "w") as f: json.dump({"collected_at": datetime.now(BJT).isoformat(), "signals": sigs}, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(sigs)} signals to {sp}")
    else:
        report = run_backtest(True)
        print(format_report(report))
        if args.json:
            print("\nJSON:\n" + json.dumps({"total": report.total, "by_horizon": report.by_horizon, "by_strategy": report.by_strategy, "by_direction": report.by_direction}, indent=2, ensure_ascii=False))
        if args.save:
            with open(args.save, "w") as f: json.dump({"total": report.total, "by_horizon": report.by_horizon, "by_strategy": report.by_strategy, "by_direction": report.by_direction, "details": report.details}, f, indent=2, ensure_ascii=False)
            print(f"\nSaved to {args.save}")
