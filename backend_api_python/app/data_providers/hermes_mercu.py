"""
Hermes MerCu Data Provider.
Reads Mercu.win market anomaly data for signal generation.
API: cryptosniper-epic.zeabur.app (discovered 2026-06-13)
"""
from __future__ import annotations

import os
import json
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

import requests

logger = logging.getLogger(__name__)

BJT = timezone(timedelta(hours=8))

# Mercu.win API base (discovered from browser network tab)
MERCU_API_BASE = os.getenv(
    "MERCU_API_BASE",
    "https://cryptosniper-epic.zeabur.app"
)

# Endpoints discovered:
# /api/radar/anomaly-v4?limit=100  - state anomalies
# /api/radar/momentum?window=15m   - momentum data
# /api/radar/surge?limit=5         - surge ranking
# /api/radar/rank                  - rank data
# /api/radar/dashboard             - dashboard summary
# /api/radar/briefs                - brief signals
# /api/radar/brief                 - single brief
# /api/radar/plaza?limit=10        - plaza data  
# /api/radar/deep?limit=5          - deep analysis
# /api/radar/coin-icons            - coin icon mappings

ENDPOINTS = {
    "anomaly": "/api/radar/anomaly-v4",
    "momentum": "/api/radar/momentum",
    "surge": "/api/radar/surge",
    "rank": "/api/radar/rank",
    "dashboard": "/api/radar/dashboard",
    "briefs": "/api/radar/briefs",
    "plaza": "/api/radar/plaza",
    "deep": "/api/radar/deep",
}

# State scoring from signal document
STATE_SCORES = {
    "底部吸筹": 5, "现货托底": 4, "多头共振": 5,
    "多头焦点": 3, "空头共振": -5, "空头焦点": -3,
    "顶部派发": -6,
}

TAG_SCORES = {
    "ACCUMULATION": 3, "STEALTH_BUILD_LONG": 4,
    "BULL_OPEN": 2, "DISTRIBUTION": -4,
    "SHORT_SQUEEZE": 3, "WHIPSAW": -2, "CHOP_NOISE": -1,
}

TRANSITION_BONUS = {
    ("ACCUM", "BULL"): 4, ("ACCUM", "DISTRIB"): -3,
    ("BULL", "DISTRIB"): -5, ("DISTRIB", "BULL"): 2,
    ("DISTRIB", "ACCUM"): 1,
}

STAGE_THRESHOLDS = [
    (12, "主升确认"), (8, "偏多启动"), (5, "吸筹/试盘"),
    (0, "震荡"), (-5, "风险区"), (-100, "派发/出货"),
]


def get_stage(score: int) -> str:
    for threshold, stage in STAGE_THRESHOLDS:
        if score >= threshold:
            return stage
    return "派发/出货"


class MerCuClient:
    """HTTP client for Mercu.win API."""

    def __init__(self, base_url: str = MERCU_API_BASE, token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("MERCU_JWT_TOKEN", "")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; Hermes/1.0)",
            "Accept": "application/json",
            "Origin": "https://mercu.win",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.warning(f"MerCu API call failed: {endpoint} - {e}")
            return {}

    def get_anomalies(self, limit: int = 100) -> List[dict]:
        data = self._get(ENDPOINTS["anomaly"], {"limit": limit})
        return data.get("state_anomalies", []) if isinstance(data, dict) else []

    def get_momentum(self, window: str = "15m") -> List[dict]:
        data = self._get(ENDPOINTS["momentum"], {"window": window})
        return data if isinstance(data, list) else []

    def get_surge(self, limit: int = 5) -> List[dict]:
        data = self._get(ENDPOINTS["surge"], {"limit": limit})
        return data if isinstance(data, list) else []

    def get_rank(self) -> dict:
        return self._get(ENDPOINTS["rank"])

    def get_dashboard(self) -> dict:
        return self._get(ENDPOINTS["dashboard"])

    def get_plaza(self, limit: int = 10) -> List[dict]:
        data = self._get(ENDPOINTS["plaza"], {"limit": limit})
        return data if isinstance(data, list) else []

    def get_deep(self, limit: int = 5) -> List[dict]:
        data = self._get(ENDPOINTS["deep"], {"limit": limit})
        return data if isinstance(data, list) else []


class HermesSignalEngine:
    """Process Mercu.win data into trading signals."""

    def __init__(self, client: MerCuClient = None):
        self.client = client or MerCuClient()
        self._cache: Dict[str, dict] = {}
        self._cache_ts: float = 0
        self._cache_ttl: float = 30  # 30 second cache

    def _cached_call(self, key: str, fetcher, *args, force: bool = False):
        now = time.time()
        if not force and key in self._cache and (now - self._cache_ts) < self._cache_ttl:
            return self._cache.get(key)
        result = fetcher(*args)
        self._cache[key] = result
        self._cache_ts = now
        return result

    def get_all_data(self) -> dict:
        """Fetch all Mercu data in one call (cached)."""
        return {
            "anomalies": self._cached_call("anomalies", self.client.get_anomalies, 100),
            "momentum": self._cached_call("momentum", self.client.get_momentum, "15m"),
            "surge": self._cached_call("surge", self.client.get_surge, 5),
            "rank": self._cached_call("rank", self.client.get_rank),
            "plaza": self._cached_call("plaza", self.client.get_plaza, 10),
        }

    def score_coin(self, state_events: List[dict], momentum_data: dict = None) -> dict:
        """Score a single coin based on Mercu state events."""
        score = 0
        details = []
        tags_seen = set()
        prev_state = None

        for event in state_events:
            state = event.get("state", "")
            tag = event.get("tag", "")
            cohort = event.get("cohort_label", "")

            if state in STATE_SCORES:
                pts = STATE_SCORES[state]
                score += pts
                details.append(f"{state}({pts:+d})")

            if tag in TAG_SCORES:
                pts = TAG_SCORES[tag]
                score += pts
                details.append(f"tag:{tag}({pts:+d})")
                tags_seen.add(tag)

            # Transition bonus
            if prev_state:
                transition = self._state_to_group(prev_state), self._state_to_group(state)
                if transition in TRANSITION_BONUS:
                    pts = TRANSITION_BONUS[transition]
                    score += pts
                    details.append(f"transition:{transition[0]}->{transition[1]}({pts:+d})")

            prev_state = state

        # Surge bonus
        surge_mult = event.get("surge_mult", 1.0) if state_events else 1.0
        if surge_mult > 1.5:
            score += 3
            details.append(f"surge:{surge_mult:.1f}x(+3)")

        stage = get_stage(score)
        return {
            "score": score,
            "stage": stage,
            "details": details,
            "tags": list(tags_seen),
        }

    @staticmethod
    def _state_to_group(state: str) -> str:
        if state in ("底部吸筹", "现货托底"):
            return "ACCUM"
        if state in ("多头共振", "多头焦点"):
            return "BULL"
        if state in ("顶部派发",):
            return "DISTRIB"
        if state in ("空头共振", "空头焦点"):
            return "BEAR"
        return "NEUTRAL"

    def generate_signals(self) -> List[dict]:
        """Generate trading signals from all Mercu data."""
        data = self.get_all_data()
        anomalies = data.get("anomalies", [])
        momentum = data.get("momentum", [])
        surge = data.get("surge", [])

        # Build surge lookup
        surge_map = {}
        for s in surge:
            sym = s.get("symbol", "").upper()
            surge_map[sym] = s.get("surge_mult", 1.0)

        # Group anomalies by symbol
        by_symbol: Dict[str, List[dict]] = {}
        for a in anomalies:
            sym = a.get("symbol", "").upper()
            if sym:
                by_symbol.setdefault(sym, []).append(a)

        signals = []
        for sym, events in by_symbol.items():
            result = self.score_coin(events)
            if abs(result["score"]) >= 5:  # Only emit meaningful signals
                direction = "LONG" if result["score"] > 0 else "SHORT"
                # Get price from momentum if available
                price = None
                for m in momentum:
                    if m.get("symbol", "").upper() == sym:
                        price = m.get("price")
                        break

                signals.append({
                    "symbol": sym,
                    "direction": direction,
                    "score": result["score"],
                    "stage": result["stage"],
                    "details": result["details"],
                    "tags": result["tags"],
                    "price": price,
                    "surge_mult": surge_map.get(sym, 1.0),
                    "timestamp": datetime.now(BJT).isoformat(),
                })

        # Sort by absolute score
        signals.sort(key=lambda s: abs(s["score"]), reverse=True)
        return signals


# Singleton
_engine: Optional[HermesSignalEngine] = None


def get_hermes_engine() -> HermesSignalEngine:
    global _engine
    if _engine is None:
        _engine = HermesSignalEngine()
    return _engine
