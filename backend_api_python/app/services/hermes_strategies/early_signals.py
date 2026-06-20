"""Early Signals V3 - Document-based leading indicators for pre-positioning.

Implements ALL signals from 《山寨币庄家异动数据库 V1》that were NOT
in the original indicators.py. These detect accumulation, distribution,
stage transitions, and smart money behavior BEFORE price moves.

Signals implemented (score from document):
  bottom_accumulation    +5  底部吸筹
  spot_support           +4  现货托底  
  bull_resonance         +5  多头共振
  large_buy_wall         +4  大笔买入挂单
  short_squeeze          +3  空头被挤压
  mid_trap_recovery      +2  中陷阱后拉回
  high_trap_single       -1  高陷阱单次
  high_trap_consecutive  -4  连续高陷阱
  top_distribution       -6  顶部派发
  oi_divergence          -5  OI背离
  vol_moderate_expand    +3  Vol温和放大(领先)
  stage_transition       +4  阶段转换(派发→吸筹)
  multi_tf_resonance     +3  多TF共振增强
  bear_resonance         -5  空头共振
"""
from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Coin types from document
YAOBI_COINS = frozenset({"COAI","MEGA","LAB","RAVE","BEAT","HYPE","XPL","PLAY","HUMA"})
SENTIMENT_COINS = frozenset({"TRADOOR","ESPORTS","1000PEPE","1000LUNC"})
INSTITUTIONAL_COINS = frozenset({"TAO","SUI","FET","RNDR","APT","INJ","NEAR"})
TOP_DISTRIBUTION_COINS = frozenset({"TRUMP","BEAT"})


@dataclass
class EarlySignal:
    """A single early/leading signal detection result."""
    name: str
    score: int           # Document-based score
    direction: str       # LONG / SHORT / NEUTRAL
    confidence: str      # high / medium / low
    reason: str
    stage: str = ""      # accumulation / washout / breakout / top / distribution / crash


@dataclass  
class StageDetection:
    """Stage classification result based on document rules."""
    stage: str           # accumulation / washout / breakout / blowoff / distribution / crash
    score: int           # Confidence score for this stage
    evidence: List[str]  # Signals that led to this classification
    entry_zone: str      # wait / accumulate / entry / exit / avoid


# ═══════════════════════════════════════════════════════════════
# SIGNAL DETECTION FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def detect_bottom_accumulation(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """+5 底部吸筹 - detect accumulation at bottom.
    
    Document: 底部吸筹 signal present in anomaly data.
    Enhanced: check for OI quietly building + price not moving much.
    """
    anomalies = mercu_data.get("anomalies", [])
    for a in anomalies:
        sym = (a.get("symbol") or a.get("sym","")).upper()
        if sym != symbol:
            continue
        dim = a.get("main_dim","")
        d = a.get("main_direction",0)
        percentile = float(a.get("percentile",0))
        
        # Document: 底部吸筹 = OI moderate buildup + low percentile context
        if dim == "oi" and d > 0 and 0.85 <= percentile < 0.98:
            # Check if price is flat (within momentum data)
            mom_map = indicators.get("momentum_map",{})
            mom = mom_map.get(symbol,{})
            change_pct = abs(mom.get("change_pct",99))
            
            if change_pct < 2.0:  # Price barely moved = stealth accumulation
                return EarlySignal(
                    "底部吸筹", 5, "LONG", "high",
                    f"OI温和建仓p{percentile:.0%}+价格不动",
                    stage="accumulation"
                )
            elif change_pct < 5.0:
                return EarlySignal(
                    "底部吸筹", 4, "LONG", "medium",
                    f"OI建仓p{percentile:.0%}",
                    stage="accumulation"
                )
    return None


def detect_spot_support(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """+4 现货托底 - spot market buying support.
    
    Document: 现货托底 = real buying, accumulation.
    Check plaza data for spot flow direction.
    """
    plaza_map = indicators.get("plaza_map",{})
    pl = plaza_map.get(symbol,{})
    spot_flow = pl.get("spot_flow","")
    
    if "buy" in str(spot_flow).lower() or "多" in str(spot_flow):
        strength = pl.get("strength",0)
        if strength > 60:
            return EarlySignal("现货托底", 4, "LONG", "high",
                f"现货持续买入(s{strength})", stage="accumulation")
        return EarlySignal("现货托底", 3, "LONG", "medium",
            f"现货买入", stage="accumulation")
    return None


def detect_bull_resonance(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """+5 多头共振 - bull resonance across multiple dimensions.
    
    Document: 多头共振 = 主升启动 at low, 高位诱多 at high.
    We distinguish by checking if price already ran up.
    """
    mom_map = indicators.get("momentum_map",{})
    mom = mom_map.get(symbol,{})
    resonance_count = mom.get("resonance_count",0)
    side = mom.get("side","")
    change_pct = abs(mom.get("change_pct",0))
    
    if side == "up" and resonance_count >= 3:
        # Check if already extended
        if change_pct < 5.0:
            return EarlySignal("多头共振", 5, "LONG", "high",
                f"多TF共振启动(r{resonance_count})", stage="breakout")
        elif change_pct < 10.0:
            return EarlySignal("多头共振", 3, "LONG", "medium",
                f"多TF共振(r{resonance_count},已涨{change_pct:.1f}%)", stage="breakout")
        else:
            return EarlySignal("多头共振", -2, "SHORT", "medium",
                f"高位诱多(r{resonance_count},已涨{change_pct:.1f}%)", stage="blowoff")
    return None


def detect_large_buy_wall(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """+4 大笔买入挂单 - large buy orders on orderbook.
    
    Document: 大笔买入挂单 = strong buy support.
    Check surge data for bid wall presence.
    """
    surge_map = indicators.get("surge_map",{})
    sg = surge_map.get(symbol,{})
    bid_wall = sg.get("bid_wall",0)
    
    if bid_wall > 15:  # 15%+ bid wall
        return EarlySignal("大笔买入挂单", 4, "LONG", "high",
            f"bid挂单墙{bid_wall}%", stage="accumulation")
    elif bid_wall > 8:
        return EarlySignal("大笔买入挂单", 2, "LONG", "medium",
            f"bid挂单{bid_wall}%", stage="accumulation")
    return None


def detect_short_squeeze(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """+3 空头被挤压 - shorts being squeezed.
    
    Document: 空头被挤压 = fuel for upside.
    Check OI drop + price up (shorts covering).
    """
    oi_flow = indicators.get("oi_flow",{})
    oi = oi_flow.get(symbol,{})
    mom_map = indicators.get("momentum_map",{})
    mom = mom_map.get(symbol,{})
    
    oi_dir = oi.get("direction","")
    price_dir = mom.get("side","")
    
    # Short squeeze: OI dropping but price rising = shorts covering
    if oi_dir == "down" and price_dir == "up":
        return EarlySignal("空头被挤压", 3, "LONG", "high",
            "OI降+价涨→空头平仓", stage="breakout")
    return None


def detect_mid_trap_recovery(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """+2 中陷阱后拉回 - recovery after mid-level trap.
    
    Document: 中陷阱=洗盘区, 拉回=买入机会.
    Check for trap signal followed by price recovery.
    """
    surge_map = indicators.get("surge_map",{})
    sg = surge_map.get(symbol,{})
    has_trap = sg.get("mid_trap",False)
    rhythm = sg.get("rhythm","")
    
    if has_trap and "加速" in rhythm:
        return EarlySignal("中陷阱后拉回", 2, "LONG", "medium",
            "陷阱后加速恢复", stage="washout")
    return None


def detect_high_trap(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """-1/-4 高陷阱 - high trap signals (single vs consecutive).
    
    Document: 高陷阱单次=-1, 连续高陷阱=-4.
    """
    surge_map = indicators.get("surge_map",{})
    sg = surge_map.get(symbol,{})
    trap_count = sg.get("high_trap_count",0)
    
    if trap_count >= 3:
        return EarlySignal("连续高陷阱", -4, "SHORT", "high",
            f"连续{trap_count}次高陷阱→顶", stage="blowoff")
    elif trap_count >= 1:
        return EarlySignal("高陷阱单次", -1, "SHORT", "medium",
            f"高陷阱×{trap_count}", stage="distribution")
    return None


def detect_top_distribution(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """-6 顶部派发 - top distribution detection.
    
    Document: 顶部派发 = strong selling at top.
    Check anomaly data for distribution signals.
    """
    anomalies = mercu_data.get("anomalies",[])
    for a in anomalies:
        sym = (a.get("symbol") or a.get("sym","")).upper()
        if sym != symbol:
            continue
        dim = a.get("main_dim","")
        d = a.get("main_direction",0)
        percentile = float(a.get("percentile",0))
        grade = a.get("grade","")
        
        # OI dropping from high percentile
        if dim == "oi" and d < 0 and percentile > 0.95 and grade in ("SS","S"):
            # Check price context
            mom_map = indicators.get("momentum_map",{})
            mom = mom_map.get(symbol,{})
            change_pct = abs(mom.get("change_pct",0))
            
            if change_pct > 10:  # Already ran up significantly
                return EarlySignal("顶部派发", -6, "SHORT", "high",
                    f"高位OI派发p{percentile:.0%}(已涨{change_pct:.0f}%)",
                    stage="distribution")
            return EarlySignal("顶部派发", -4, "SHORT", "medium",
                f"OI派发p{percentile:.0%}", stage="distribution")
    return None


def detect_oi_divergence(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """-5 OI背离 - OI-price divergence.
    
    Document: OI背离 = top warning.
    Price making new high but OI not confirming (or dropping).
    """
    oi_flow = indicators.get("oi_flow",{})
    oi = oi_flow.get(symbol,{})
    mom_map = indicators.get("momentum_map",{})
    mom = mom_map.get(symbol,{})
    
    oi_dir = oi.get("direction","")
    price_dir = mom.get("side","")
    change_pct = abs(mom.get("change_pct",0))
    
    # Bearish divergence: price up but OI dropping
    if price_dir == "up" and oi_dir == "down" and change_pct > 5:
        return EarlySignal("OI背离", -5, "SHORT", "high",
            f"价涨OI降→顶部背离(已涨{change_pct:.1f}%)",
            stage="distribution")
    # Bullish divergence: price down but OI building
    if price_dir == "down" and oi_dir == "up":
        return EarlySignal("OI背离", 3, "LONG", "medium",
            "价跌OI增→底部背离", stage="accumulation")
    return None


def detect_vol_moderate_expand(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """+3 Vol温和放大 - moderate volume expansion (LEADING signal).
    
    Document: Vol温和放大 at low = 点火/试盘 (test fire).
    This is a LEADING signal that happens BEFORE big moves.
    """
    anomalies = mercu_data.get("anomalies",[])
    for a in anomalies:
        sym = (a.get("symbol") or a.get("sym","")).upper()
        if sym != symbol:
            continue
        dim = a.get("main_dim","")
        d = a.get("main_direction",0)
        percentile = float(a.get("percentile",0))
        grade = a.get("grade","")
        
        if dim == "vol" and 0.75 <= percentile < 0.92 and grade in ("S","A"):
            mom_map = indicators.get("momentum_map",{})
            mom = mom_map.get(symbol,{})
            change_pct = abs(mom.get("change_pct",0))
            
            if change_pct < 3.0:  # Price hasn't moved yet = LEADING
                return EarlySignal("Vol温和放大", 3, "LONG", "high",
                    f"量先行价未动→点火前兆(p{percentile:.0%})",
                    stage="accumulation")
    return None


def detect_stage_transition(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """+4 阶段转换 - stage transition detection.
    
    Document: 派发→吸筹 is a major turning point.
    Check signal sequences for stage transitions.
    """
    surge_map = indicators.get("surge_map",{})
    sg = surge_map.get(symbol,{})
    stage_seq = sg.get("stage_sequence",[])
    
    # Look for distribution→accumulation transition
    if len(stage_seq) >= 2:
        prev = stage_seq[-2] if len(stage_seq) >= 2 else ""
        curr = stage_seq[-1] if stage_seq else ""
        
        # 派发→吸筹 = major reversal signal
        if "派发" in str(prev) and "吸筹" in str(curr):
            return EarlySignal("阶段转换", 4, "LONG", "high",
                "派发→吸筹转折", stage="accumulation")
        # 吸筹→多头 = breakout signal
        if "吸筹" in str(prev) and "多头" in str(curr):
            return EarlySignal("阶段转换", 3, "LONG", "high",
                "吸筹→多头启动", stage="breakout")
        # 多头→派发 = top signal
        if "多头" in str(prev) and "派发" in str(curr):
            return EarlySignal("阶段转换", -4, "SHORT", "high",
                "多头→派发见顶", stage="distribution")
    
    return None


def detect_multi_tf_resonance_enhanced(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """+3 多TF共振增强 - enhanced multi-timeframe resonance.
    
    Document: Multiple timeframes confirming same direction.
    This is different from basic momentum resonance - checks OI+Vol+Price alignment.
    """
    mom_map = indicators.get("momentum_map",{})
    mom = mom_map.get(symbol,{})
    resonance_count = mom.get("resonance_count",0)
    
    if resonance_count >= 2:
        anomalies = mercu_data.get("anomalies",[])
        oi_dir = 0; vol_dir = 0
        for a in anomalies:
            sym = (a.get("symbol") or a.get("sym","")).upper()
            if sym != symbol:
                continue
            if a.get("main_dim") == "oi":
                oi_dir = a.get("main_direction",0)
            if a.get("main_dim") == "vol":
                vol_dir = a.get("main_direction",0)
        
        # OI + Vol + Price all aligned = strong resonance
        side = mom.get("side","")
        if side == "up" and oi_dir > 0 and vol_dir > 0 and resonance_count >= 3:
            return EarlySignal("多TF共振增强", 3, "LONG", "high",
                f"OI+Vol+Price共振×{resonance_count}TF", stage="breakout")
        elif side == "down" and oi_dir < 0 and vol_dir < 0 and resonance_count >= 3:
            return EarlySignal("多TF共振增强", -3, "SHORT", "high",
                f"OI+Vol+Price共振×{resonance_count}TF", stage="crash")
    
    return None


def detect_bear_resonance(symbol: str, mercu_data: dict, indicators: dict) -> Optional[EarlySignal]:
    """-5 空头共振 - bear resonance.
    
    Document: 空头共振 at low = 低位诱空 (fake sell), at high = 下跌加速.
    """
    mom_map = indicators.get("momentum_map",{})
    mom = mom_map.get(symbol,{})
    resonance_count = mom.get("resonance_count",0)
    side = mom.get("side","")
    change_pct = abs(mom.get("change_pct",0))
    
    if side == "down" and resonance_count >= 3:
        if change_pct > 10.0:
            return EarlySignal("空头共振", -5, "SHORT", "high",
                f"下跌加速(r{resonance_count})", stage="crash")
        elif change_pct < 3.0:
            # Low price + bear resonance = potential trap (bullish reversal)
            return EarlySignal("空头共振", 2, "LONG", "medium",
                f"低位诱空(r{resonance_count})", stage="washout")
        else:
            return EarlySignal("空头共振", -3, "SHORT", "medium",
                f"空头共振(r{resonance_count})", stage="distribution")
    return None


# ═══════════════════════════════════════════════════════════════
# STAGE DETECTION (6 stages from document)
# ═══════════════════════════════════════════════════════════════

def classify_stage(symbol: str, mercu_data: dict, indicators: dict,
                   early_signals: List[EarlySignal]) -> StageDetection:
    """Classify which of 6 stages the coin is currently in.
    
    Document stages: 吸筹期 → 洗盘期 → 主升期 → 赶顶期 → 派发期 → 出货崩盘期
    """
    signal_names = {s.name for s in early_signals}
    signal_score = sum(s.score for s in early_signals)
    
    # Build evidence from signals
    evidence = [f"{s.name}({s.score:+d})" for s in early_signals]
    
    # ── Stage 1: 吸筹期 (Accumulation) ──
    if ("底部吸筹" in signal_names or "现货托底" in signal_names):
        acc_count = len([s for s in early_signals if s.stage == "accumulation"])
        if acc_count >= 2:
            return StageDetection("accumulation", min(acc_count * 4, 15), evidence, "accumulate")
        if acc_count >= 1:
            return StageDetection("accumulation", acc_count * 3, evidence, "wait")
    
    # ── Stage 2: 赶顶期 (Blowoff Top) ──
    if "连续高陷阱" in signal_names or ("高陷阱" in str(evidence) and "多头共振" in signal_names):
        return StageDetection("blowoff", -8, evidence, "exit")
    
    # ── Stage 3: 洗盘期 (Washout/Shakeout) ──
    mid_trap_signals = [s for s in early_signals if "中陷阱" in s.name]
    if mid_trap_signals:
        has_recovery = "中陷阱后拉回" in signal_names
        if has_recovery:
            return StageDetection("washout", 8, evidence, "entry")
        return StageDetection("washout", 4, evidence, "wait")
    
    # ── Stage 4: 主升期 (Breakout/Main Uptrend) ──
    if ("多头共振" in signal_names and signal_score > 5):
        return StageDetection("breakout", min(signal_score + 5, 20), evidence, "entry")
    
    # ── Stage 5: 派发期 (Distribution) ──
    if "顶部派发" in signal_names or "OI背离" in signal_names:
        dist_count = len([s for s in early_signals if s.stage == "distribution"])
        if dist_count >= 2:
            return StageDetection("distribution", -10, evidence, "avoid")
        return StageDetection("distribution", -6, evidence, "exit")
    
    # ── Stage 6: 出货崩盘期 (Crash) ──
    if "空头共振" in signal_names and signal_score < -3:
        return StageDetection("crash", -12, evidence, "avoid")
    
    # ── Default: check net direction ──
    if signal_score > 3:
        return StageDetection("accumulation", signal_score, evidence, "wait")
    elif signal_score < -3:
        return StageDetection("distribution", signal_score, evidence, "avoid")
    
    return StageDetection("neutral", 0, evidence, "wait")


# ═══════════════════════════════════════════════════════════════
# COMBINED EARLY ENTRY SCORER
# ═══════════════════════════════════════════════════════════════

def run_all_early_signals(symbol: str, mercu_data: dict, indicators: dict) -> Tuple[List[EarlySignal], StageDetection]:
    """Run ALL document-based early signals for a symbol.
    
    Returns: (list of detected signals, stage classification)
    """
    detectors = [
        detect_bottom_accumulation,
        detect_spot_support,
        detect_bull_resonance,
        detect_large_buy_wall,
        detect_short_squeeze,
        detect_mid_trap_recovery,
        detect_high_trap,
        detect_top_distribution,
        detect_oi_divergence,
        detect_vol_moderate_expand,
        detect_stage_transition,
        detect_multi_tf_resonance_enhanced,
        detect_bear_resonance,
    ]
    
    signals = []
    for detector in detectors:
        try:
            result = detector(symbol, mercu_data, indicators)
            if result:
                signals.append(result)
        except Exception as e:
            logger.debug(f"{detector.__name__}({symbol}): {e}")
    
    stage = classify_stage(symbol, mercu_data, indicators, signals)
    
    return signals, stage


def get_early_entry_score(symbol: str, mercu_data: dict, indicators: dict) -> dict:
    """Get a comprehensive early entry score with all document signals.
    
    Returns dict with:
      total_score: combined document score
      direction: LONG/SHORT/NEUTRAL
      stage: accumulation/washout/breakout/blowoff/distribution/crash
      action: wait/accumulate/entry/exit/avoid
      signals: list of detected early signals
      leading_count: number of leading (pre-move) signals
    """
    signals, stage = run_all_early_signals(symbol, mercu_data, indicators)
    
    total = sum(s.score for s in signals)
    leading = [s for s in signals if "leading" in str(s.__dict__) or s.stage == "accumulation"]
    
    direction = "LONG" if total > 2 else "SHORT" if total < -2 else "NEUTRAL"
    
    return {
        "total_score": total,
        "direction": direction,
        "stage": stage.stage,
        "action": stage.entry_zone,
        "signals": [{"name": s.name, "score": s.score, "direction": s.direction,
                      "confidence": s.confidence, "reason": s.reason} for s in signals],
        "leading_count": len([s for s in signals if s.stage == "accumulation"]),
        "evidence": stage.evidence,
    }


