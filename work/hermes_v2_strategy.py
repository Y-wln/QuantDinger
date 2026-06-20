# 小鹿量化分析引擎 v2 — 合并优化版
# smc_analyzer + analyze 去重合并 · 修 Bug · 补全指标
# QuantDinger on_bar 策略

import math
import numpy as np

# ═══════════════════════════════════════════
# 基础指标（去重，只保留一套）
# ═══════════════════════════════════════════

def ema(vals, p):
    if len(vals) < p: return None
    k = 2.0 / (p + 1); r = vals[0]
    for v in vals[1:]: r = v * k + r * (1 - k)
    return r

def ema_series(vals, p):
    if len(vals) < p: return [None] * len(vals)
    k = 2.0 / (p + 1); res = [None] * len(vals)
    res[p - 1] = sum(vals[:p]) / float(p)
    for i in range(p, len(vals)): res[i] = vals[i] * k + res[i - 1] * (1 - k)
    return res

def sma(vals, p):
    if len(vals) < p: return None
    return sum(vals[-p:]) / float(p)

def rsi_val(closes, period=14):
    if len(closes) < period + 1: return 50
    ch = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    ag = sum(c for c in ch[:period] if c > 0) / float(period)
    al = sum(-c for c in ch[:period] if c < 0) / float(period)
    if al == 0: return 100
    for i in range(period, len(ch)):
        c = ch[i]; ag = (ag * (period - 1) + max(c, 0)) / float(period)
        al = (al * (period - 1) + max(-c, 0)) / float(period)
    return 50 if al == 0 else 100 - 100 / (1 + ag / al)

def atr_val(highs, lows, closes, period=14):
    n = len(closes)
    if n < period + 1: return 0
    tr = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])) for i in range(1, n)]
    return sum(tr[-period:]) / float(period)

def atr_series(highs, lows, closes, period=14):
    n = len(closes)
    if n < period + 1: return [0] * n
    trs = [0.0] * n
    for i in range(1, n):
        trs[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    res = [0.0] * n
    for i in range(period, n): res[i] = sum(trs[i - period + 1:i + 1]) / float(period)
    return res

def bollinger(closes, period=20, std_dev=2):
    if len(closes) < period: return None
    sma20 = sma(closes, period)
    std = np.std(closes[-period:])
    cur = closes[-1]
    upper = sma20 + std_dev * std
    lower = sma20 - std_dev * std
    percent_b = (cur - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
    return {"upper": round(upper, 2), "middle": round(sma20, 2), "lower": round(lower, 2),
            "percent_b": round(percent_b, 3), "width": round((upper - lower) / sma20 * 100, 1)}

# ═══════════════════════════════════════════
# 维加斯通道
# ═══════════════════════════════════════════

def vegas_channel(closes):
    if len(closes) < 676: return None
    e12 = ema(closes, 12); e144 = ema(closes, 144)
    e169 = ema(closes, 169); e576 = ema(closes, 576); e676 = ema(closes, 676)
    cur = closes[-1]
    if cur > e144 and e144 > e169 and e144 > e576 and e169 > e676:
        direction = "强势多头"
    elif cur > e144 and e144 > e169:
        direction = "多头"
    elif cur < e144 and e144 < e169 and e144 < e576 and e169 < e676:
        direction = "强势空头"
    elif cur < e144 and e144 < e169:
        direction = "空头"
    else:
        direction = "震荡"
    return {
        "e12": round(e12, 2), "e144": round(e144, 2), "e169": round(e169, 2),
        "e576": round(e576, 2), "e676": round(e676, 2), "direction": direction,
        "channel_w": round((e169 - e144) / e144 * 100, 2) if e144 else 0
    }

# ═══════════════════════════════════════════
# Choppiness Index（市场状态：趋势/震荡）
# ═══════════════════════════════════════════

def choppiness_index(highs, lows, closes, period=14):
    n = len(closes)
    if n < period + 1: return None
    atr_arr = atr_series(highs, lows, closes, 1)
    window_atr = sum(atr_arr[-period:])
    highest = max(highs[-period:]); lowest = min(lows[-period:])
    if highest == lowest: return 50
    ci = 100 * math.log10(window_atr / (highest - lowest)) / math.log10(period)
    ci = max(0, min(100, ci))
    if ci > 61.8: regime = "震荡"
    elif ci < 38.2: regime = "趋势"
    else: regime = "过渡"
    return {"ci": round(ci, 1), "regime": regime}

# ═══════════════════════════════════════════
# BOS/CHoCH 结构突破检测
# ═══════════════════════════════════════════

def detect_bos_choch(highs, lows, closes, lookback=7):
    n = len(closes)
    if n < lookback * 2 + 1: return None

    def find_swings(arr, is_high):
        points = []
        for i in range(lookback, n - lookback):
            if is_high:
                if all(arr[i] >= arr[j] for j in range(i - lookback, i + lookback + 1) if j != i):
                    points.append((i, arr[i]))
            else:
                if all(arr[i] <= arr[j] for j in range(i - lookback, i + lookback + 1) if j != i):
                    points.append((i, arr[i]))
        return points

    sh = find_swings(highs, True)
    sl = find_swings(lows, False)

    breaks = []
    structure = "未知"
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            if sh[j][1] > sh[i][1]:
                breaks.append({"type": "bullish", "idx": sh[j][0], "price": sh[j][1]})
                structure = "上升"
            elif sh[j][1] < sh[i][1]:
                breaks.append({"type": "bearish_structure", "idx": sh[j][0], "price": sh[j][1]})
                structure = "下降"
    for i in range(len(sl)):
        for j in range(i + 1, len(sl)):
            if sl[j][1] < sl[i][1]:
                breaks.append({"type": "bearish", "idx": sl[j][0], "price": sl[j][1]})
                structure = "下降"
            elif sl[j][1] > sl[i][1]:
                breaks.append({"type": "bullish_structure", "idx": sl[j][0], "price": sl[j][1]})
                structure = "上升"

    recent_break = breaks[-1] if breaks else None
    return {"structure": structure, "breaks": breaks[-5:], "last": recent_break}

# ═══════════════════════════════════════════
# SuperTrend
# ═══════════════════════════════════════════

def supertrend(highs, lows, closes, period=10, multiplier=3.0):
    n = len(closes)
    if n < period + 1: return None
    atr_arr = atr_series(highs, lows, closes, period)
    hl_avg = [(highs[i] + lows[i]) / 2.0 for i in range(n)]
    upper = [0.0] * n; lower = [0.0] * n; trend = [0] * n
    for i in range(period, n):
        upper[i] = hl_avg[i] + multiplier * atr_arr[i]
        lower[i] = hl_avg[i] - multiplier * atr_arr[i]
        if i > period:
            upper[i] = min(upper[i], upper[i - 1]) if closes[i - 1] > upper[i - 1] else upper[i]
            lower[i] = max(lower[i], lower[i - 1]) if closes[i - 1] < lower[i - 1] else lower[i]
        if closes[i] > upper[i - 1] if i > period else closes[i] > upper[i]:
            trend[i] = 1
        elif closes[i] < lower[i - 1] if i > period else closes[i] < lower[i]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1] if i > period else 0
    return {"direction": "多头" if trend[-1] == 1 else "空头",
            "upper": round(upper[-1], 2), "lower": round(lower[-1], 2),
            "price": closes[-1], "atr": round(atr_arr[-1], 2)}

# ═══════════════════════════════════════════
# MACD
# ═══════════════════════════════════════════

def macd_analysis(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal: return None
    fast_ema = ema_series(closes, fast)
    slow_ema = ema_series(closes, slow)
    macd_line = [fast_ema[i] - slow_ema[i] if fast_ema[i] and slow_ema[i] else 0 for i in range(len(closes))]
    signal_line = ema_series(macd_line, signal)
    hist = macd_line[-1] - signal_line[-1] if signal_line[-1] else 0
    if macd_line[-1] > signal_line[-1]:
        sig = "bullish"
    elif macd_line[-1] < signal_line[-1]:
        sig = "bearish"
    else:
        sig = "neutral"
    return {"signal": sig, "hist": round(float(hist), 4),
            "macd": round(float(macd_line[-1]), 4),
            "cross": "金叉" if macd_line[-2] <= signal_line[-2] and macd_line[-1] > signal_line[-1]
                     else ("死叉" if macd_line[-2] >= signal_line[-2] and macd_line[-1] < signal_line[-1] else "")}

# ═══════════════════════════════════════════
# KDJ
# ═══════════════════════════════════════════

def kdj_analysis(highs, lows, closes, n=9):
    if len(closes) < n: return None
    k_vals = [50.0] * n; d_vals = [50.0] * n
    for i in range(n, len(closes)):
        hh = max(highs[i - n + 1:i + 1]); ll = min(lows[i - n + 1:i + 1])
        rsv = (closes[i] - ll) / (hh - ll) * 100 if hh != ll else 50
        k_vals.append(2 / 3.0 * k_vals[-1] + 1 / 3.0 * rsv)
        d_vals.append(2 / 3.0 * d_vals[-1] + 1 / 3.0 * k_vals[-1])
    k, d = k_vals[-1], d_vals[-1]
    j = 3 * k - 2 * d
    if k < 20 and d < 20: zone = "超卖"
    elif k > 80 and d > 80: zone = "超买"
    else: zone = "中性"
    return {"k": round(k, 1), "d": round(d, 1), "j": round(j, 1), "zone": zone,
            "cross": "金叉" if k_vals[-2] <= d_vals[-2] and k_vals[-1] > d_vals[-1]
                     else ("死叉" if k_vals[-2] >= d_vals[-2] and k_vals[-1] < d_vals[-1] else "")}

# ═══════════════════════════════════════════
# RSI Divergence（修复：使用滚动RSI序列）
# ═══════════════════════════════════════════

def rsi_divergence(closes, lookback=5):
    n = len(closes)
    if n < 40: return []
    rs_vals = []
    for i in range(14, n): rs_vals.append(rsi_val(closes[:i + 1], 14))

    def find_swings(arr, lb):
        pts = []
        for i in range(lb, len(arr) - lb):
            if all(arr[i] >= arr[j] for j in range(i - lb, i + lb + 1) if j != i):
                pts.append((i + 14, arr[i]))
            if all(arr[i] <= arr[j] for j in range(i - lb, i + lb + 1) if j != i):
                pts.append((i + 14, arr[i]) if arr[i] < arr[i-lb] else ())
        return [p for p in pts if p]

    price_swings = [(i, closes[i]) for i in range(n) if i >= lookback and i < n - lookback
                    and (all(closes[i] >= closes[j] for j in range(i - lookback, i + lookback + 1) if j != i)
                         or all(closes[i] <= closes[j] for j in range(i - lookback, i + lookback + 1) if j != i))]

    results = []
    for i in range(1, len(price_swings)):
        p1, p2 = price_swings[i - 1], price_swings[i]
        r1_idx = p1[0] - 14; r2_idx = p2[0] - 14
        if r1_idx < 0 or r2_idx < 0 or r1_idx >= len(rs_vals) or r2_idx >= len(rs_vals):
            continue
        r1, r2 = rs_vals[r1_idx], rs_vals[r2_idx]
        if p2[1] > p1[1] and r2 < r1:
            results.append({"type": "顶背离", "signal": "bearish"})
            break
        if p2[1] < p1[1] and r2 > r1:
            results.append({"type": "底背离", "signal": "bullish"})
            break
    return results

# ═══════════════════════════════════════════
# 共识评分（7维度加权）
# ═══════════════════════════════════════════

def consensus_score(vegas, ci, bos, st, macd_r, kdj_r, bb, rsi_div, rsi_v):
    score = 0
    reasons = []

    # 1. 维加斯 (25%)
    if vegas and vegas["direction"] in ("强势多头", "多头"):
        score += 25; reasons.append("维加斯多头 +25")
    elif vegas and vegas["direction"] in ("强势空头", "空头"):
        score -= 25; reasons.append("维加斯空头 -25")

    # 2. 市场状态 (10%)
    if ci and ci["regime"] == "趋势":
        score += 10; reasons.append("趋势行情 +10")
    elif ci and ci["regime"] == "震荡":
        score += 3; reasons.append("震荡市 +3")

    # 3. 结构分析 (15%)
    if bos and bos["structure"] == "上升":
        score += 15; reasons.append("上升结构 +15")
    elif bos and bos["structure"] == "下降":
        score -= 15; reasons.append("下降结构 -15")
    if bos and bos["last"] and bos["last"].get("type") == "bearish_structure":
        score -= 8; reasons.append("结构破位 -8")
    elif bos and bos["last"] and bos["last"].get("type") == "bullish_structure":
        score += 8; reasons.append("结构突破 +8")

    # 4. SuperTrend (10%)
    if st and st["direction"] == "多头":
        score += 10; reasons.append("SuperTrend多头 +10")
    elif st:
        score -= 10; reasons.append("SuperTrend空头 -10")

    # 5. MACD+KDJ (15%)
    if macd_r and macd_r["signal"] == "bullish":
        score += 8; reasons.append("MACD看涨 +8")
    elif macd_r and macd_r["signal"] == "bearish":
        score -= 8; reasons.append("MACD看跌 -8")
    if kdj_r and kdj_r["zone"] == "超卖":
        score += 7; reasons.append("KDJ超卖 +7")
    elif kdj_r and kdj_r["zone"] == "超买":
        score -= 7; reasons.append("KDJ超买 -7")

    # 6. RSI+布林带 (15%)
    
    if bb and bb["percent_b"] < 0.2:
        score += 8; reasons.append("布林下轨 +8")
    elif bb and bb["percent_b"] > 0.8:
        score -= 8; reasons.append("布林上轨 -8")
    if rsi_div:
        for rd in rsi_div:
            if rd["signal"] == "bullish":
                score += 7; reasons.append("RSI底背离 +7")
            elif rd["signal"] == "bearish":
                score -= 7; reasons.append("RSI顶背离 -7")

    # 7. Choppiness微调 (5%) — 趋势加强得分
    if ci and ci["regime"] == "趋势":
        if score > 0: score += 5
        elif score < 0: score -= 5

    score = max(-100, min(100, score))
    return {"score": score, "signal": "📈 偏多" if score > 20 else ("📉 偏空" if score < -20 else "📊 中性"),
            "reasons": reasons}

# ═══════════════════════════════════════════
# 主策略 on_bar
# ═══════════════════════════════════════════



def on_bar(ctx, bar):
    
    bars = ctx.bars(700)
    if len(bars) < 200:
        return

    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    volumes = [b["volume"] for b in bars]
    

    cur_price = closes[-1]

    # 所有指标计算
    vegas = vegas_channel(closes)
    ci = choppiness_index(highs, lows, closes)
    bos = detect_bos_choch(highs, lows, closes)
    st = supertrend(highs, lows, closes)
    macd_r = macd_analysis(closes)
    kdj_r = kdj_analysis(highs, lows, closes)
    bb = bollinger(closes)
    rsi_v = rsi_val(closes, 14)
    atr = atr_val(highs, lows, closes, 14)
    rsi_div = rsi_divergence(closes)

    # 共识评分
    cs = consensus_score(vegas, ci, bos, st, macd_r, kdj_r, bb, rsi_div, rsi_v)

    # 输出检查清单
    ctx.log("=" * 50)
    ctx.log(f"🦌 {ctx.symbol} | ${cur_price:,.2f} | {bar['timestamp']}")
    ctx.log(f"共识评分: {cs['score']:+.0f} {cs['signal']}")
    ctx.log("")

    # 指标面板
    ctx.log("── 核心指标 ──")
    if vegas:
        ctx.log(f"维加斯: {vegas['direction']} | 通道宽 {vegas.get('channel_w', 0):+.1f}%")
    if ci:
        ctx.log(f"市场状态: {ci['regime']} (CI={ci['ci']})")
    if bos:
        ctx.log(f"结构: {bos['structure']} | 最近: {bos['last']['type'] if bos['last'] else '无'}")
    if st:
        ctx.log(f"SuperTrend: {st['direction']} | ATR={st['atr']}")
    ctx.log(f"RSI: {rsi_v:.0f} | ATR: {atr:.2f}")

    ctx.log("")
    ctx.log("── 动量指标 ──")
    if macd_r:
        ctx.log(f"MACD: {macd_r['signal']} | hist={macd_r['hist']:.4f} | {macd_r['cross']}")
    if kdj_r:
        ctx.log(f"KDJ: K={kdj_r['k']} D={kdj_r['d']} J={kdj_r['j']} | {kdj_r['zone']} | {kdj_r['cross']}")
    if bb:
        ctx.log(f"布林: 上{bb['upper']} 中{bb['middle']} 下{bb['lower']} | %b={bb['percent_b']}")

    # 背离
    if rsi_div:
        for rd in rsi_div:
            ctx.log(f"⚠️ RSI{rd['type']} ({rd['signal']})")
    else:
        ctx.log("RSI: 无背离")

    # 评分分解
    ctx.log("")
    ctx.log("── 共识评分分解 ──")
    for r in cs["reasons"]:
        ctx.log(f"  {r}")

    ctx.log("")
    ctx.log(f"综合: 共识{cs['score']:+.0f}分 {cs['signal']}")
    ctx.log("🦌 仅客观数据，不做交易建议")
