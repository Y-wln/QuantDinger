"""V3 Indicators - MerCu-powered technical indicators (no exchange needed).

Ported from V2 work/hermes-v2/indicators/ but adapted for MerCu-only data.
All indicators work with the computed data from MerCuDataBridge._compute_indicators().

Indicators:
  momentum_score  - Multi-timeframe momentum from MerCu boards
  surge_score     - Rhythm/acceleration scoring from surge data
  plaza_score     - Smart money divergence detection
  oi_score        - OI flow analysis for accumulation/distribution
  cvd_score       - CVD proxy from price+OI correlation
  composite_score - Weighted combination of all above
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class IndicatorResult:
    """Single indicator output."""
    name: str
    score: int          # -10 to +10
    direction: str      # LONG / SHORT / NEUTRAL
    confidence: str     # low / medium / high
    reason: str


def momentum_score(symbol: str, indicators: dict, resonance_weight: float = 2.0) -> IndicatorResult:
    """Score from MerCu momentum boards + resonance.
    
    Ported from V2 momentum.py - uses price strength + multi-TF resonance.
    """
    mom_map = indicators.get("momentum_map", {})
    mom = mom_map.get(symbol, {})
    
    if not mom:
        return IndicatorResult("momentum", 0, "NEUTRAL", "low", "")
    
    strength = mom.get("strength", 0)
    resonance_count = mom.get("resonance_count", 0)
    side = mom.get("side", "neutral")
    change_pct = abs(mom.get("change_pct", 0))
    
    score = 0
    direction = "NEUTRAL"
    reasons = []
    
    # Base score from strength (0-100 scale)
    if strength >= 98:
        base = 5
    elif strength >= 90:
        base = 3
    elif strength >= 80:
        base = 2
    else:
        base = 1
    
    # Resonance bonus (multi-timeframe confirmation)
    if resonance_count >= 4:
        base += 4
        reasons.append(f"共振{resonance_count}TF")
    elif resonance_count >= 3:
        base += 3
        reasons.append(f"共振{resonance_count}TF")
    elif resonance_count >= 2:
        base += 2
        reasons.append(f"共振{resonance_count}TF")
    
    # Direction
    if side == "up":
        score = base
        direction = "LONG"
        reasons.append(f"动量↑{strength:.0f}")
    elif side == "down":
        score = -base
        direction = "SHORT"
        reasons.append(f"动量↓{strength:.0f}")
    
    # Change % modifier
    if change_pct > 5:
        score = score + (1 if score > 0 else -1)
    
    confidence = "high" if resonance_count >= 3 else "medium" if resonance_count >= 1 else "low"
    
    return IndicatorResult("momentum", score, direction, confidence, "|".join(reasons) if reasons else "")


def surge_score(symbol: str, indicators: dict) -> IndicatorResult:
    """Score from MerCu surge data - rhythm/acceleration.
    
    Ported from V2 launch.py surge detection.
    Rhythm patterns: 加速冒头(strongest) > 节奏维持 > 降温中(weakest)
    """
    surge_map = indicators.get("surge_map", {})
    sg = surge_map.get(symbol, {})
    
    if not sg:
        return IndicatorResult("surge", 0, "NEUTRAL", "low", "")
    
    rhythm = sg.get("rhythm", "")
    accel = sg.get("accel", 0)
    total = sg.get("total", 0)
    direction = sg.get("dir", "up")
    
    score = 0
    reasons = []
    
    # Rhythm scoring
    if "加速冒头" in rhythm or "极速冒头" in rhythm:
        score = 5
        reasons.append("加速冒头")
    elif "爆发" in rhythm:
        score = 4
        reasons.append("爆发")
    elif "节奏维持" in rhythm:
        score = 3
        reasons.append("节奏维持")
    elif "降温" in rhythm:
        score = -2
        reasons.append("降温")
        direction = "down" if direction == "up" else "up"  # Reverse
    
    # Acceleration bonus
    if accel > 1.5:
        score += 2
    elif accel > 1.0:
        score += 1
    elif accel < 0.5:
        score -= 1
    
    # Total spark bonus
    if total > 10:
        score += 1
    
    if direction == "down":
        score = -score
    
    dir_str = "LONG" if score > 0 else "SHORT" if score < 0 else "NEUTRAL"
    confidence = "high" if accel > 1.5 else "medium" if accel > 1.0 else "low"
    
    return IndicatorResult("surge", score, dir_str, confidence, "|".join(reasons) if reasons else rhythm)


def plaza_score(symbol: str, indicators: dict) -> IndicatorResult:
    """Score from MerCu Plaza data - smart money vs retail divergence.
    
    Ported from V2 concept of smart money tracking.
    Bullish: smart money buying, retail selling (divergence)
    Bearish: smart money selling, retail buying
    """
    plaza_map = indicators.get("plaza_map", {})
    pl = plaza_map.get(symbol, {})
    
    if not pl:
        return IndicatorResult("plaza", 0, "NEUTRAL", "low", "")
    
    sentiment = pl.get("sentiment", "")
    strength = pl.get("strength", 0)
    smart = pl.get("smart_money", "")
    has_div = pl.get("divergence", False)
    
    score = 0
    direction = "NEUTRAL"
    reasons = []
    
    # Smart money direction
    if "多" in str(smart) or "bull" in str(smart).lower():
        score = 3
        direction = "LONG"
        reasons.append("Plaza多")
    elif "空" in str(smart) or "bear" in str(smart).lower():
        score = -3
        direction = "SHORT"
        reasons.append("Plaza空")
    
    # Divergence = stronger signal
    if has_div:
        score = score * 2 if score != 0 else 0
        reasons.append("SM分歧")
    
    # Strength modifier (0-100)
    if strength > 80:
        score = score + (1 if score > 0 else -1 if score < 0 else 0)
    
    confidence = "high" if has_div else "medium"
    
    return IndicatorResult("plaza", score, direction, confidence, "|".join(reasons) if reasons else "")


def oi_flow_score(symbol: str, indicators: dict, anomalies: list) -> IndicatorResult:
    """Score from OI flow - accumulation vs distribution.
    
    Ported from V2 oi_analysis.py.
    Extreme OI moves signal potential reversals (mean reversion) or trend continuation.
    """
    oi_flow = indicators.get("oi_flow", {})
    oi = oi_flow.get(symbol, {})
    
    score = 0
    direction = "NEUTRAL"
    reasons = []
    
    # Find specific anomaly for this symbol
    for a in anomalies:
        sym = (a.get("symbol") or a.get("sym", "")).upper()
        if sym != symbol or a.get("main_dim") != "oi":
            continue
        
        d = a.get("main_direction", 0)
        grade = a.get("grade", "")
        val = abs(a.get("main_value", 0))
        percentile = float(a.get("percentile", 0))
        rank = a.get("self_history_rank", 99)
        
        # Extreme OI drop = potential bounce (mean reversion)
        if d < 0 and grade == "SS" and rank <= 3:
            score += 10
            direction = "LONG"
            reasons.append(f"OI暴跌#{rank}→反弹")
        elif d < 0 and percentile > 0.98:
            score += 6
            direction = "LONG"
            reasons.append(f"OI急跌p{percentile:.0%}")
        
        # Extreme OI surge = potential reversal  
        elif d > 0 and grade == "SS" and rank <= 3:
            score -= 8
            direction = "SHORT"
            reasons.append(f"OI暴涨#{rank}→回落")
        
        # Moderate OI building = accumulation
        elif d > 0 and percentile > 0.95 and grade in ("SS", "S"):
            score += 5
            direction = "LONG"
            reasons.append(f"OI吸筹p{percentile:.0%}")
        
        # Moderate OI declining = distribution
        elif d < 0 and percentile > 0.95 and grade in ("SS", "S"):
            score -= 5
            direction = "SHORT"
            reasons.append(f"OI派发p{percentile:.0%}")
        
        break  # Only use the strongest anomaly
    
    confidence = "high" if abs(score) >= 8 else "medium" if abs(score) >= 4 else "low"
    
    return IndicatorResult("oi_flow", score, direction, confidence, "|".join(reasons) if reasons else "")


def cvd_proxy_score(symbol: str, indicators: dict, anomalies: list) -> IndicatorResult:
    """Score from CVD proxy - price direction + OI correlation.
    
    Ported from V2 cvd.py concept.
    Strong buy = price up + volume/OI up
    Strong sell = price down + volume/OI down
    """
    cvd = indicators.get("cvd_proxy", {})
    signal = cvd.get(symbol, "")
    
    score = 0
    direction = "NEUTRAL"
    
    if signal == "strong_buy":
        score = 6
        direction = "LONG"
    elif signal == "strong_sell":
        score = -6
        direction = "SHORT"
    elif signal == "buy":
        score = 3
        direction = "LONG"
    elif signal == "sell":
        score = -3
        direction = "SHORT"
    
    confidence = "high" if "strong" in signal else "medium" if signal else "low"
    
    return IndicatorResult("cvd_proxy", score, direction, confidence, signal)


def composite_score(symbol: str, mercu_data: dict, indicators: dict) -> Tuple[int, str, List[str]]:
    """Combine all indicators into a composite score (-40 to +40).
    
    Ported from V2 scorer.py - weighted aggregation.
    
    Returns: (total_score, direction, all_reasons)
    """
    results = []
    
    # Run all indicators
    results.append(momentum_score(symbol, indicators))
    results.append(surge_score(symbol, indicators))
    results.append(plaza_score(symbol, indicators))
    results.append(oi_flow_score(symbol, indicators, mercu_data.get("anomalies", [])))
    results.append(cvd_proxy_score(symbol, indicators, mercu_data.get("anomalies", [])))
    
    # Weighted aggregation
    total = 0
    all_reasons = []
    
    for r in results:
        if r.score != 0:
            weight = 1.5 if r.confidence == "high" else 1.0 if r.confidence == "medium" else 0.5
            total += r.score * weight
            if r.reason:
                all_reasons.append(f"[{r.name}]{r.reason}")
    
    total = int(total)
    direction = "LONG" if total > 0 else "SHORT" if total < 0 else "NEUTRAL"
    
    return total, direction, all_reasons


# ── Score interpretation ────────────────────────────────────

def interpret_score(score: int) -> str:
    """Human-readable score interpretation."""
    if score >= 30:
        return "HOT主升确认"
    elif score >= 20:
        return "LONG偏多启动"
    elif score >= 10:
        return "LONG?偏多观望"
    elif score <= -30:
        return "COLD主跌确认"
    elif score <= -20:
        return "SHORT偏空启动"
    elif score <= -10:
        return "SHORT?偏空观望"
    else:
        return "NEUTRAL方向不明"

