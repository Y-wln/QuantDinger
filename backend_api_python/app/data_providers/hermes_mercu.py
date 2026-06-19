"""
Hermes MerCu Signal Engine V2
================================
Full implementation of "山寨币庄家异动数据库 V1" document.
6 stages, 21 signal scores, coin type classification, OI multi-timeframe.

Data source: Mercu.win API (cryptosniper-epic.zeabur.app)
"""
from __future__ import annotations

import os
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

import requests

logger = logging.getLogger(__name__)

BJT = timezone(timedelta(hours=8))
MERCU_API_BASE = os.getenv("MERCU_API_BASE", "https://cryptosniper-epic.zeabur.app")

# ============================================================
# 1. COIN TYPE CLASSIFICATION (文档第一节)
# ============================================================

class CoinType(Enum):
    YAOBI_CONTROL = "妖币控盘型"       # OI/市值高，吸筹→洗盘→主升→派发
    SENTIMENT_HARVEST = "情绪收割型"   # 高陷阱、顶部派发、Vol爆发
    INSTITUTIONAL_TREND = "机构趋势型" # 现货托底、资金流、走势慢
    HIGH_DISTRIBUTION = "高位派发型"   # OI暴跌、顶部背离、拉升后出货


# Known coin classifications (文档第六节)
KNOWN_COIN_TYPES: Dict[str, CoinType] = {
    "COAI": CoinType.YAOBI_CONTROL,
    "MEGA": CoinType.YAOBI_CONTROL,
    "LAB": CoinType.YAOBI_CONTROL,
    "RAVE": CoinType.YAOBI_CONTROL,
    "BEAT": CoinType.YAOBI_CONTROL,
    "TRADOOR": CoinType.SENTIMENT_HARVEST,
    "ESPORTS": CoinType.SENTIMENT_HARVEST,
    "TAO": CoinType.INSTITUTIONAL_TREND,
    "SUI": CoinType.INSTITUTIONAL_TREND,
    "TRUMP": CoinType.HIGH_DISTRIBUTION,
}


# ============================================================
# 2. SIGNAL SCORES (文档第五节)
# ============================================================

SIGNAL_SCORES: Dict[str, int] = {
    # 底部/吸筹信号
    "底部吸筹": 5,
    "现货托底": 4,
    "多头共振": 5,
    "多头焦点": 3,
    "多头开仓": 2,

    # OI signals (positive)
    "OI暴涨_5_10": 2,       # 5%~10%
    "OI暴涨_10_plus": 4,    # 10%以上
    "OI暴涨_15_plus": 6,    # 15%以上(妖币级)

    # Volume signals
    "Vol爆发": 3,
    "Vol极端放大": 4,

    # Order book signals
    "大笔买入挂单": 4,
    "空头被挤压": 3,
    "逼空": 3,

    # Recovery signals
    "中陷阱后拉回": 2,

    # Negative signals
    "高陷阱单次": -1,
    "连续高陷阱": -4,
    "顶部派发": -6,
    "空头共振": -5,
    "空头焦点": -3,
    "OI背离": -5,
    "现货净流出": -4,
    "OI暴跌_10_plus": -4,
    "OI暴跌_20_plus": -6,
    "多头爆仓": -5,
}


# ============================================================
# 3. STAGE THRESHOLDS (文档第五节)
# ============================================================

STAGE_THRESHOLDS: List[Tuple[int, str]] = [
    (12, "主升确认"),
    (8, "偏多启动"),
    (4, "吸筹/试盘"),
    (0, "震荡"),
    (-5, "风险区"),
    (-100, "派发/出货"),
]


# ============================================================
# 4. OI PERCENTAGE RULES (文档第三节)
# ============================================================

# (min_pct, max_pct, label, score_if_positive, score_if_negative)
OI_RULES_5M = [
    (0, 2, "噪音", 0, 0),
    (3, 5, "有资金进场", 1, -1),
    (5, 8, "明显异动", 2, -2),
    (8, 12, "强操盘", 3, -3),
    (12, 100, "拉盘/砸盘前兆", 4, -4),
]

OI_RULES_15M = [
    (3, 5, "轻度建仓", 1, -1),
    (5, 10, "主力动作", 2, -2),
    (10, 15, "主升/逼空", 3, -3),
    (15, 100, "妖币级别异动", 5, -5),
]

OI_RULES_1H = [
    (5, 10, "趋势增强", 2, -1),
    (10, 20, "强控盘", 3, -2),
    (20, 30, "妖币启动", 4, -3),
    (30, 100, "极端行情", 5, -5),
]


def get_oi_score(pct_change: float, timeframe: str) -> int:
    """Calculate OI score based on percentage change and timeframe."""
    rules = {"5m": OI_RULES_5M, "15m": OI_RULES_15M, "1h": OI_RULES_1H}.get(timeframe, OI_RULES_15M)
    abs_pct = abs(pct_change)
    direction = 1 if pct_change > 0 else -1

    for min_pct, max_pct, label, pos_score, neg_score in rules:
        if min_pct <= abs_pct < max_pct:
            return pos_score if direction > 0 else neg_score
    return 0


def get_stage(score: int) -> str:
    for threshold, stage in STAGE_THRESHOLDS:
        if score >= threshold:
            return stage
    return "派发/出货"


def classify_coin(symbol: str, cohort_label: str = None, tags: List[str] = None) -> CoinType:
    """Classify coin based on known types + behavior patterns."""
    sym = symbol.upper()
    if sym in KNOWN_COIN_TYPES:
        return KNOWN_COIN_TYPES[sym]

    if cohort_label == "微币":
        return CoinType.YAOBI_CONTROL

    tags = tags or []
    if "WHIPSAW" in tags or "CHOP_NOISE" in tags:
        return CoinType.SENTIMENT_HARVEST

    if cohort_label is None:
        return CoinType.INSTITUTIONAL_TREND

    return CoinType.YAOBI_CONTROL


# ============================================================
# 5. STAGE DETECTION (文档第四节)
# ============================================================

@dataclass
class StageDetection:
    """Result of stage detection for a coin."""
    stage: str                    # 吸筹期/洗盘期/主升期/赶顶期/派发期/出货崩盘期
    confidence: int               # 0-100
    signals_present: List[str]    # Which signals triggered this stage
    action: str                   # 建议操作


def detect_stage(events: List[dict]) -> StageDetection:
    """
    Detect which stage a coin is in based on signal combinations.
    
    Priority order (文档第四节):
    1. 吸筹期: 底部吸筹 + 现货托底 + OI小幅暴涨 + Vol温和 + 价格不涨
    2. 洗盘期: OI暴跌 + 价格不破支撑 + 现货托底 + Vol不持续跌
    3. 主升期: 多头共振 + OI暴涨 + Vol爆发 + 现货托底 + 价格突破
    4. 赶顶期: 连续高陷阱 + OI暴涨 + 价格远离均线 + Vol极端
    5. 派发期: 顶部派发 + OI背离 + 现货流出 + 高位横盘
    6. 出货崩盘期: OI暴跌 + 现货流出 + 合约抄底 + 价格续跌
    """
    labels = [e.get("main_dim_label", "") for e in events]
    dims = [e.get("main_dim", "") for e in events]
    directions = [e.get("main_direction", 0) for e in events]
    joined = " ".join(labels)

    has_oi_surge = any("OI 暴涨" in l or "OI暴涨" in l for l in labels)
    has_oi_crash = any("OI 暴跌" in l or "OI暴跌" in l for l in labels)
    has_vol_surge = any("Vol 爆发" in l or "成交量爆发" in l for l in labels)
    has_bottom_accum = "底部吸筹" in joined
    has_spot_support = "现货托底" in joined
    has_bull_resonance = "多头共振" in joined
    has_top_distribute = "顶部派发" in joined
    has_high_trap = "高陷阱" in joined
    has_oi_divergence = "OI背离" in joined
    has_spot_outflow = "现货流出" in joined

    # 主升期 (highest priority match first)
    if has_bull_resonance and has_oi_surge and has_vol_surge:
        return StageDetection("主升期", 80, ["多头共振", "OI暴涨", "Vol爆发", "现货托底"], "右侧确认，可以跟随")

    # 赶顶期
    if has_high_trap and has_oi_surge:
        return StageDetection("赶顶期", 70, ["连续高陷阱", "OI暴涨", "价格远离均线"], "不追高，只减仓")

    # 出货崩盘期
    if has_oi_crash and has_spot_outflow:
        return StageDetection("出货崩盘期", 75, ["OI暴跌", "现货流出", "合约抄底"], "反弹多为出货反抽")

    # 派发期
    if has_top_distribute and has_oi_divergence:
        return StageDetection("派发期", 75, ["顶部派发", "OI背离", "现货流出"], "不接飞刀")
    if has_top_distribute:
        return StageDetection("派发期", 60, ["顶部派发", "高位横盘"], "不接飞刀")

    # 洗盘期
    if has_oi_crash and has_spot_support and has_vol_surge:
        return StageDetection("洗盘期", 65, ["OI暴跌", "不破支撑", "现货托底"], "支撑不破是低吸区")

    # 吸筹期
    if has_bottom_accum and has_spot_support and not has_oi_crash:
        return StageDetection("吸筹期", 70, ["底部吸筹", "现货托底", "OI小幅暴涨"], "可以重点观察")

    # Partial matches
    if has_bottom_accum:
        return StageDetection("吸筹期(初步)", 50, ["底部吸筹"], "观察确认")
    if has_bull_resonance:
        return StageDetection("偏多启动", 55, ["多头共振"], "关注后续信号")
    if has_top_distribute or has_spot_outflow:
        return StageDetection("风险区", 50, ["派发信号"], "减仓观望")

    return StageDetection("震荡", 30, [], "等待方向明朗")


# ============================================================
# 6. CIRCUIT BREAKER (防雪崩)
# ============================================================

class CircuitBreaker:
    """Prevents cascading failures when API is down."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 300):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures = 0
        self._last_failure_time = 0.0
        self._state = "CLOSED"  # CLOSED / OPEN / HALF_OPEN

    @property
    def is_open(self) -> bool:
        if self._state == "OPEN":
            if time.time() - self._last_failure_time > self.cooldown_seconds:
                self._state = "HALF_OPEN"
                logger.info("Circuit breaker: OPEN -> HALF_OPEN (cooldown elapsed)")
            else:
                return True
        return False

    def record_success(self):
        if self._state == "HALF_OPEN":
            logger.info("Circuit breaker: HALF_OPEN -> CLOSED (success)")
        self._failures = 0
        self._state = "CLOSED"

    def record_failure(self):
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self.failure_threshold:
            self._state = "OPEN"
            logger.warning(f"Circuit breaker OPEN after {self._failures} failures, cooldown {self.cooldown_seconds}s")


# ============================================================
# 7. MERCu API CLIENT
# ============================================================

class MerCuClient:
    """HTTP client for Mercu.win API with circuit breaker."""

    def __init__(self, base_url: str = MERCU_API_BASE, token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("MERCU_JWT_TOKEN", "")
        self._token_file = "/tmp/mercu_live_token.txt"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; Hermes/1.0)",
            "Accept": "application/json",
            "Origin": "https://mercu.win",
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        self.circuit = CircuitBreaker()

    def _get(self, path: str, params: dict = None) -> dict:
        if os.path.exists(self._token_file):
            try:
                with open(self._token_file) as f:
                    t = f.read().strip()
                    if t and len(t) > 50:
                        self.token = t
                        self.session.headers["Authorization"] = f"Bearer {t}"
            except: pass
        if self.circuit.is_open:
            logger.warning(f"Circuit breaker open, skipping: {path}")
            return {}

        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            self.circuit.record_success()
            return resp.json()
        except requests.RequestException as e:
            self.circuit.record_failure()
            logger.warning(f"MerCu API failed: {path} - {e}")
            return {}

    def get_anomalies(self, limit: int = 100) -> List[dict]:
        data = self._get("/api/radar/anomaly-v4", {"limit": limit})
        if isinstance(data, dict):
            return data.get("data", data.get("state_anomalies", []))
        return data if isinstance(data, list) else []

    def get_momentum(self, window: str = "15m") -> dict:
        return self._get("/api/radar/momentum", {"window": window})

    def get_surge(self, limit: int = 5) -> List[dict]:
        data = self._get("/api/radar/surge", {"limit": limit})
        return data if isinstance(data, list) else []

    def get_rank(self) -> dict:
        return self._get("/api/radar/rank")

    def get_dashboard(self) -> dict:
        return self._get("/api/radar/dashboard")

    def get_briefs(self) -> List[dict]:
        data = self._get("/api/radar/briefs")
        return data if isinstance(data, list) else []

    def get_plaza(self, limit: int = 10) -> List[dict]:
        data = self._get("/api/radar/plaza", {"limit": limit})
        return data if isinstance(data, list) else []

    def get_deep(self, limit: int = 5) -> List[dict]:
        data = self._get("/api/radar/deep", {"limit": limit})
        return data if isinstance(data, list) else []


# ============================================================
# 8. SIGNAL ENGINE
# ============================================================

@dataclass
class CoinSignal:
    """Complete signal analysis for one coin."""
    symbol: str
    coin_type: CoinType
    score: int
    stage: str
    stage_detail: StageDetection
    direction: str  # LONG / SHORT / NEUTRAL
    price: Optional[float] = None
    signals_triggered: List[str] = field(default_factory=list)
    oi_pct_5m: float = 0.0
    oi_pct_15m: float = 0.0
    oi_pct_1h: float = 0.0
    surge_mult: float = 1.0
    market_cap: Optional[str] = None
    timestamp: str = ""


class HermesSignalEngine:
    """
    Full signal engine implementing "山寨币庄家异动数据库 V1".
    
    Processes Mercu.win anomaly + momentum data into:
    - Coin type classification
    - 6-stage detection
    - 21-signal scoring
    - Multi-timeframe OI analysis
    """

    def __init__(self, client: MerCuClient = None):
        self.client = client or MerCuClient()
        self._cache: Dict[str, dict] = {}
        self._cache_ts: float = 0
        self._cache_ttl: float = 30

    def _cached(self, key: str, fetcher, *args) -> dict:
        now = time.time()
        if key in self._cache and (now - self._cache_ts) < self._cache_ttl:
            return self._cache[key]
        result = fetcher(*args)
        self._cache[key] = result
        self._cache_ts = now
        return result

    def get_all_data(self) -> dict:
        return {
            "anomalies": self._cached("anomalies", self.client.get_anomalies, 100),
            "momentum": self._cached("momentum", self.client.get_momentum, "15m"),
            "surge": self._cached("surge", self.client.get_surge, 5),
            "rank": self._cached("rank", self.client.get_rank),
            "plaza": self._cached("plaza", self.client.get_plaza, 10),
        }

    def score_events(self, symbol: str, events: List[dict]) -> Tuple[int, List[str]]:
        """Score all events for a coin using the document scoring model."""
        score = 0
        triggered = []

        for event in events:
            label = event.get("main_dim_label", "")
            dim = event.get("main_dim", "")
            direction = event.get("main_direction", 0)
            pct = abs(event.get("pct_to_ref", 0))
            window = event.get("main_window", "15m")
            grade = event.get("grade", "")

            # ---- OI signals (文档第二节 + 第三节) ----
            if dim == "oi":
                if "暴" in label:  # OI暴涨
                    if pct >= 15:
                        score += SIGNAL_SCORES["OI暴涨_15_plus"]
                        triggered.append(f"OI暴涨{pct:.0f}%")
                    elif pct >= 10:
                        score += SIGNAL_SCORES["OI暴涨_10_plus"]
                        triggered.append(f"OI暴涨{pct:.0f}%")
                    elif pct >= 5:
                        score += SIGNAL_SCORES["OI暴涨_5_10"]
                        triggered.append(f"OI暴涨{pct:.0f}%")
                elif "跌" in label:  # OI暴跌
                    if pct >= 20:
                        score += SIGNAL_SCORES["OI暴跌_20_plus"]
                        triggered.append(f"OI暴跌{pct:.0f}%")
                    elif pct >= 10:
                        score += SIGNAL_SCORES["OI暴跌_10_plus"]
                        triggered.append(f"OI暴跌{pct:.0f}%")
                    else:
                        score -= 1
                        triggered.append(f"OI小跌{pct:.0f}%")

            # ---- Volume signals ----
            elif dim == "vol":
                if direction > 0:
                    if pct >= 20:
                        score += SIGNAL_SCORES["Vol极端放大"]
                        triggered.append(f"Vol极端{pct:.0f}%")
                    else:
                        score += SIGNAL_SCORES["Vol爆发"]
                        triggered.append(f"Vol爆发{pct:.0f}%")

            # ---- Grade bonus ----
            if grade == "SS":
                score += 2
                triggered.append("grade:SS")
            elif grade == "S":
                score += 1
                triggered.append("grade:S")

        return score, triggered

    def analyze_coin(self, symbol: str, events: List[dict], momentum_data: dict = None) -> CoinSignal:
        """Complete single-coin analysis."""
        sym = symbol.upper()

        # Score events
        score, triggered = self.score_events(sym, events)

        # Classify coin
        cohort = next((e.get("cohort_label") for e in events if e.get("cohort_label")), None)
        tags = [e.get("main_tag") for e in events if e.get("main_tag")]
        coin_type = classify_coin(sym, cohort, tags)

        # Detect stage
        stage_detail = detect_stage(events)

        # OI multi-timeframe
        oi_5m = sum(e.get("pct_to_ref", 0) for e in events if e.get("main_dim") == "oi" and e.get("main_window") == "5m")
        oi_15m = sum(e.get("pct_to_ref", 0) for e in events if e.get("main_dim") == "oi" and e.get("main_window") == "15m")
        oi_1h = sum(e.get("pct_to_ref", 0) for e in events if e.get("main_dim") == "oi" and e.get("main_window") == "1h")

        # Direction
        if score >= 8:
            direction = "LONG"
        elif score <= -5:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"

        # Price lookup from momentum
        price = None
        mc = None
        if momentum_data:
            boards = momentum_data.get("boards", {})
            for side in ("priceUp", "priceDn", "oiUp", "oiDn"):
                for item in boards.get(side, []):
                    if item.get("sym", "").upper() == sym:
                        val = item.get("val", "")
                        if val and "%" in str(val):
                            try:
                                # Not price directly, but momentum data
                                pass
                            except:
                                pass
                        if item.get("mc"):
                            mc = item["mc"]

        return CoinSignal(
            symbol=sym,
            coin_type=coin_type,
            score=score,
            stage=get_stage(score),
            stage_detail=stage_detail,
            direction=direction,
            price=price,
            signals_triggered=triggered,
            oi_pct_5m=round(oi_5m, 2),
            oi_pct_15m=round(oi_15m, 2),
            oi_pct_1h=round(oi_1h, 2),
            market_cap=mc,
            timestamp=datetime.now(BJT).isoformat(),
        )

    def generate_signals(self) -> List[dict]:
        """Generate all trading signals from current Mercu data."""
        data = self.get_all_data()
        anomalies = data.get("anomalies", [])
        momentum = data.get("momentum", {})

        # Group anomalies by symbol
        by_symbol: Dict[str, List[dict]] = {}
        for a in anomalies:
            sym = (a.get("sym") or a.get("symbol") or "").replace("$", "").upper()
            if sym:
                by_symbol.setdefault(sym, []).append(a)

        signals = []
        for sym, events in by_symbol.items():
            result = self.analyze_coin(sym, events, momentum)
            if abs(result.score) >= 4:  # Filter noise
                signals.append({
                    "symbol": result.symbol,
                    "direction": result.direction,
                    "score": result.score,
                    "stage": result.stage,
                    "stage_detail": result.stage_detail.stage,
                    "stage_action": result.stage_detail.action,
                    "coin_type": result.coin_type.value,
                    "signals": result.signals_triggered,
                    "oi_5m": result.oi_pct_5m,
                    "oi_15m": result.oi_pct_15m,
                    "oi_1h": result.oi_pct_1h,
                    "price": result.price,
                    "market_cap": result.market_cap,
                    "timestamp": result.timestamp,
                })

        signals.sort(key=lambda s: abs(s["score"]), reverse=True)
        return signals


# ============================================================
# 9. SINGLETON
# ============================================================

_engine: Optional[HermesSignalEngine] = None


def get_hermes_engine() -> HermesSignalEngine:
    global _engine
    if _engine is None:
        _engine = HermesSignalEngine()
    return _engine