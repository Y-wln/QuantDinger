#!/usr/bin/env python3
"""
小鹿信息雷达 v4 — 交易级面板
扫描全市场 → 三模式检查清单 → 客观数据，不做决策
"""

import os, sys, math, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"

import requests
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BJT = timezone(timedelta(hours=8))
RADAR_DIR = Path.home() / "radar"
COINS_FILE = RADAR_DIR / "coins.txt"
DEFAULT_COINS = "BTCUSDT\nETHUSDT\nSOLUSDT\nBNBUSDT\nDOGEUSDT\nXRPUSDT\nADAUSDT\nAVAXUSDT"
B, BF = "https://api.binance.com", "https://fapi.binance.com"

S = requests.Session()
S.proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
S.headers.update({"User-Agent": "Mozilla/5.0"})

# ═══════════════════════════════
# 数据层
# ═══════════════════════════════
@st.cache_data(ttl=60)
def fetch(url, timeout=8):
    try: return S.get(url, timeout=timeout).json()
    except: return None

def fetch_klines(symbol, interval, limit=200):
    d = fetch(f"{B}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")
    if not d: return []
    return [{"o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
             "c": float(k[4]), "v": float(k[5])} for k in d]

def fetch_all_symbols():
    d = fetch(f"{BF}/fapi/v1/ticker/24hr")
    if not d: return []
    return [t["symbol"] for t in d if t["symbol"].endswith("USDT")
            and float(t.get("quoteVolume", 0)) > 5_000_000]

def fetch_24h(symbol):
    d = fetch(f"{BF}/fapi/v1/ticker/24hr?symbol={symbol}")
    if not d: return {}
    return {"price": float(d["lastPrice"]), "chg": float(d["priceChangePercent"]),
            "high": float(d["highPrice"]), "low": float(d["lowPrice"]),
            "vol": float(d["quoteVolume"])}

def fetch_funding(symbol):
    d = fetch(f"{BF}/fapi/v1/premiumIndex?symbol={symbol}")
    return float(d["lastFundingRate"]) * 100 if d else None

def fetch_oi(symbol):
    d = fetch(f"{BF}/fapi/v1/openInterest?symbol={symbol}")
    return float(d["openInterest"]) if d else None

def fetch_lsar(symbol):
    d = fetch(f"{BF}/futures/data/globalLongShortAccountRatio?symbol={symbol}&period=5m&limit=4")
    if not d: return None
    r = [float(x["longShortRatio"]) for x in d]
    return {"now": r[-1], "prev": sum(r[:3]) / 3, "trend": "up" if r[-1] > r[-3] else "down"}

def fetch_taker(symbol):
    d = fetch(f"{BF}/futures/data/takerlongshortRatio?symbol={symbol}&period=5m&limit=4")
    if not d: return None
    r = [float(x["buySellRatio"]) for x in d]
    return {"now": r[-1], "avg": sum(r) / len(r), "trend": "buy" if r[-1] > r[-3] else "sell"}

def fetch_cvd(symbol, limit=100):
    try:
        trades = fetch(f"{B}/api/v3/aggTrades?symbol={symbol}&limit={limit}")
        if not trades: return None
        cvd = 0
        for t in trades:
            m = t.get("m", False)
            cvd += float(t["q"]) if not m else -float(t["q"])
        return round(cvd, 2)
    except: return None

def fetch_fear_greed():
    r = fetch("https://api.alternative.me/fng/?limit=1")
    if not r: return None, None
    d = r["data"][0]; return int(d["value"]), d["value_classification"]

def fetch_dxy():
    r = fetch("https://api.alternative.me/dxy/")
    return float(r["dxy"]) if r and "dxy" in r else None

def fetch_news(max_items=15):
    kw = ["crypto", "bitcoin", "ethereum", "solana", "btc", "eth", "sol",
          "fed", "sec", "regulation", "etf", "tariff", "war", "hack", "blackrock",
          "加密", "比特币", "以太坊", "区块链", "币", "合约", "杠杆", "监管", "加息",
          "降息", "鲸鱼", "爆仓", "崩盘", "暴跌", "大涨"]
    items = []
    try:
        r = requests.get("https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        if r and "data" in r:
            for d in r["data"].get("roll_data", [])[:30]:
                t = d.get("title", "") or d.get("brief", "")
                if t and any(k in t for k in kw):
                    items.append({"title": t[:120], "source": "财联社", "rel": sum(1 for k in kw if k in t)})
    except: pass
    try:
        r = requests.get("https://api.theblockbeats.info/v1/newsflash/list?page=1&limit=20",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        if r and "data" in r:
            for d in r["data"].get("list", [])[:20]:
                t = d.get("title", "") or d.get("content", "")
                if t: items.append({"title": t[:120], "source": "BlockBeats", "rel": 1})
    except: pass
    items.sort(key=lambda x: x["rel"], reverse=True)
    return items[:max_items]

# ═══════════════════════════════
# 技术指标层
# ═══════════════════════════════
def ema(vals, p):
    if len(vals) < p: return None
    k = 2 / (p + 1); r = vals[0]
    for v in vals[1:]: r = v * k + r * (1 - k)
    return r

def ema_series(vals, p):
    """返回逐点EMA序列"""
    if len(vals) < p: return [None] * len(vals)
    k = 2 / (p + 1)
    res = [None] * len(vals)
    res[p - 1] = sum(vals[:p]) / p
    for i in range(p, len(vals)):
        res[i] = vals[i] * k + res[i - 1] * (1 - k)
    return res

def rsi_val(closes, period=14):
    if len(closes) < period + 1: return 50
    ch = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    ag = sum(c for c in ch[:period] if c > 0) / period
    al = sum(-c for c in ch[:period] if c < 0) / period
    if al == 0: return 100
    for i in range(period, len(ch)):
        c = ch[i]; ag = (ag * (period - 1) + max(c, 0)) / period
        al = (al * (period - 1) + max(-c, 0)) / period
    return 50 if al == 0 else 100 - 100 / (1 + ag / al)

def atr_val(kl, period=14):
    if len(kl) < period + 1: return 0
    tr = [max(kl[i]["h"] - kl[i]["l"],
              abs(kl[i]["h"] - kl[i - 1]["c"]),
              abs(kl[i]["l"] - kl[i - 1]["c"])) for i in range(1, len(kl))]
    return sum(tr[-period:]) / period

def vegas_full(kl):
    """维加斯通道完整版 — 四线 + 状态判断"""
    if len(kl) < 676: return None
    c = [k["c"] for k in kl]
    e144 = ema(c, 144); e169 = ema(c, 169)
    e576 = ema(c, 576); e676 = ema(c, 676)
    cur = c[-1]
    # 通道宽度
    channel_width = (e169 - e144) / e144 * 100
    # 排列
    if cur > e144 and e144 > e169 and e144 > e576 and e169 > e676:
        state = "强势多头"
    elif cur > e144 and e144 > e169:
        state = "多头"
    elif cur < e144 and e144 < e169 and e144 < e576 and e169 < e676:
        state = "强势空头"
    elif cur < e144 and e144 < e169:
        state = "空头"
    else:
        state = "震荡"
    return {
        "e144": e144, "e169": e169, "e576": e576, "e676": e676,
        "channel_width": channel_width, "state": state,
        "price_to_e144": (cur - e144) / e144 * 100,
    }

def hmm_analyze(kl):
    """简化HMM — 基于波动率和趋势分类市场状态"""
    if len(kl) < 80: return {"regime": "?"}
    c = np.array([k["c"] for k in kl])
    ret = np.diff(np.log(c + 1e-12))
    ret = np.append(ret, ret[-1])

    # 趋势: 价格vs EMA50
    e50_vals = ema_series(c, 50)
    trend_dev = [(c[i] - e50_vals[i]) / e50_vals[i] if e50_vals[i] else 0 for i in range(len(c))]
    trend_dev = np.array(trend_dev)

    # 波动率: 20周期标准差
    vol = np.array([np.std(ret[max(0, i-19):i+1]) for i in range(len(ret))])

    # 分类
    last_trend = trend_dev[-1]
    last_vol = vol[-1]
    med_vol = np.median(vol[-50:])

    if last_trend > 0.02 and last_vol < med_vol * 1.2:
        regime = "📈 稳定上升"
    elif last_trend > 0.02:
        regime = "📈 波动上升"
    elif last_trend < -0.02 and last_vol < med_vol * 1.2:
        regime = "📉 稳定下降"
    elif last_trend < -0.02:
        regime = "📉 波动下降"
    elif last_vol > med_vol * 1.5 and abs(last_trend) < 0.01:
        regime = "📊 高波震荡"
    elif last_vol > med_vol * 1.2:
        regime = "📊 波动震荡"
    else:
        regime = "📊 低波盘整"

    return {
        "regime": regime,
        "trend_dev": round(float(last_trend) * 100, 2),
        "vol_ratio": round(float(last_vol / (med_vol + 1e-12)), 2),
    }

def z_score_analysis(kl, lookback=100):
    """多指标z-score异常检测"""
    if len(kl) < lookback: return {}
    c = np.array([k["c"] for k in kl[-lookback:]])
    v = np.array([k["v"] for k in kl[-lookback:]])
    tr = [max(kl[i]["h"] - kl[i]["l"],
              abs(kl[i]["h"] - kl[i - 1]["c"]),
              abs(kl[i]["l"] - kl[i - 1]["c"])) for i in range(1, len(kl[-lookback:]))]
    tr.insert(0, tr[0] if tr else 0)
    tr = np.array(tr)

    ret = np.diff(np.log(c + 1e-12))
    ret = np.append(ret, ret[-1])

    def z(vals):
        return (vals[-1] - np.mean(vals)) / (np.std(vals) + 1e-12)

    price_z = z(c)
    vol_z = z(v)
    vol_chg_z = z(np.diff(v, prepend=v[0]))
    tr_z = z(tr)

    # 综合异常度
    anomalies = []
    if abs(price_z) > 2: anomalies.append(f"价格异常({price_z:+.1f}σ)")
    if vol_z > 2: anomalies.append(f"放量({vol_z:+.1f}σ)")
    if vol_z < -1.5: anomalies.append(f"缩量({vol_z:+.1f}σ)")
    if tr_z > 2: anomalies.append(f"高波({tr_z:+.1f}σ)")

    return {
        "price_z": round(float(price_z), 1),
        "vol_z": round(float(vol_z), 1),
        "anomalies": anomalies,
        "total_abs": round(abs(price_z) + abs(vol_z) + abs(tr_z), 1),
    }

# ═══════════════════════════════
# 三模式扫描引擎
# ═══════════════════════════════
def trend_scan(symbol, kl4h, kl1h, t24, funding, lsar, taker, cvd):
    """📈 趋势追踪模式"""
    c = [k["c"] for k in kl4h]
    v = vegas_full(kl4h)
    hmm = hmm_analyze(kl4h)
    zs = z_score_analysis(kl4h)
    rsi_4h = rsi_val(c, 14)
    atr_4h = atr_val(kl4h, 14)

    checks = []
    passed = 0; total = 0

    # 维加斯方向
    total += 1
    if v and v["state"] in ("强势多头", "多头"):
        checks.append(("✅", f"维加斯{v['state']}"))
        passed += 1
    elif v:
        checks.append(("❌", f"维加斯{v['state']}"))
    else:
        checks.append(("⚠️", "维加斯数据不足"))

    # EMA排列
    total += 1
    e20 = ema(c, 20); e50 = ema(c, 50)
    if e20 and e50 and e20 > e50:
        checks.append(("✅", "EMA20>EMA50 多头排列"))
        passed += 1
    elif e20 and e50:
        checks.append(("❌", "EMA死叉"))
    else:
        checks.append(("⚠️", "EMA数据不足"))

    # RSI
    total += 1
    if 40 < rsi_4h < 75:
        checks.append(("✅", f"RSI {rsi_4h:.0f} 健康"))
        passed += 1
    else:
        checks.append(("⚠️", f"RSI {rsi_4h:.0f}"))

    # 资金费率
    total += 1
    if funding is not None and -0.01 <= funding <= 0.03:
        checks.append(("✅", f"费率{funding:+.4f}% 正常"))
        passed += 1
    elif funding is not None:
        checks.append(("⚠️", f"费率{funding:+.4f}% 异常"))
    else:
        checks.append(("⚠️", "费率N/A"))

    # 多空比
    total += 1
    if lsar and lsar["trend"] == "up":
        checks.append(("✅", f"多空比上升 {lsar['now']:.2f}"))
        passed += 1
    elif lsar:
        checks.append(("⚠️", f"多空比下降 {lsar['now']:.2f}"))
    else:
        checks.append(("⚠️", "多空比N/A"))

    # Taker买卖
    total += 1
    if taker and taker["now"] > 1.1:
        checks.append(("✅", f"Taker买>卖 {taker['now']:.2f}"))
        passed += 1
    elif taker:
        checks.append(("⚠️", f"Taker比 {taker['now']:.2f}"))
    else:
        checks.append(("⚠️", "Taker N/A"))

    # CVD
    total += 1
    if cvd is not None and cvd > 0:
        checks.append(("✅", f"CVD +{cvd:,.0f} 买入累积"))
        passed += 1
    elif cvd is not None:
        checks.append(("❌", f"CVD {cvd:,.0f} 卖出"))
    else:
        checks.append(("⚠️", "CVD N/A"))

    # HMM状态
    total += 1
    if hmm and "上升" in hmm.get("regime", ""):
        checks.append(("✅", f"HMM {hmm['regime']}"))
        passed += 1
    elif hmm:
        checks.append(("❌", f"HMM {hmm['regime']}"))
    else:
        checks.append(("⚠️", "HMM N/A"))

    # z-score
    total += 1
    if zs and zs["total_abs"] < 5:
        checks.append(("✅", f"无异常(z={zs['total_abs']})"))
        passed += 1
    elif zs:
        checks.append(("⚠️", f"异常: {', '.join(zs['anomalies'][:2])}"))
    else:
        checks.append(("⚠️", "z-score N/A"))

    return {"symbol": symbol, "passed": passed, "total": total, "checks": checks,
            "price": t24.get("price", 0), "chg": t24.get("chg", 0),
            "vol": t24.get("vol", 0), "vegas": v["state"] if v else "?",
            "hmm": hmm["regime"] if hmm else "?", "rsi": rsi_4h}

def bottom_scan(symbol, kl4h, t24, funding, lsar, taker):
    """🔄 触底反弹模式"""
    c = [k["c"] for k in kl4h]
    rsi_4h = rsi_val(c, 14)
    atr_4h = atr_val(kl4h, 14)
    zs = z_score_analysis(kl4h)

    checks = []
    passed = 0; total = 0

    # RSI超卖
    total += 1
    if rsi_4h < 35:
        checks.append(("✅", f"RSI {rsi_4h:.0f} 超卖"))
        passed += 1
    elif rsi_4h < 45:
        checks.append(("⚠️", f"RSI {rsi_4h:.0f} 偏低"))
    else:
        checks.append(("❌", f"RSI {rsi_4h:.0f} 未超卖"))

    # 价格位置
    total += 1
    e50 = ema(c, 50)
    if e50:
        dev = (c[-1] - e50) / e50 * 100
        if dev < -8:
            checks.append(("✅", f"偏离EMA50 {dev:+.1f}% 深度"))
            passed += 1
        elif dev < -3:
            checks.append(("⚠️", f"偏离EMA50 {dev:+.1f}%"))
        else:
            checks.append(("❌", f"偏离EMA50 {dev:+.1f}%"))
    else:
        checks.append(("⚠️", "EMA N/A"))

    # 量缩
    total += 1
    if zs and zs["vol_z"] < -1:
        checks.append(("✅", f"缩量 {zs['vol_z']:+.1f}σ 筑底信号"))
        passed += 1
    elif zs:
        checks.append(("⚠️", f"量z={zs['vol_z']:+.1f}"))
    else:
        checks.append(("⚠️", "z-score N/A"))

    # 费率负
    total += 1
    if funding is not None and funding < -0.005:
        checks.append(("✅", f"费率{funding:+.4f}% 空头拥挤"))
        passed += 1
    elif funding is not None:
        checks.append(("⚠️", f"费率{funding:+.4f}%"))
    else:
        checks.append(("⚠️", "费率N/A"))

    # 多空比底部
    total += 1
    if lsar and lsar["now"] < 0.85:
        checks.append(("✅", f"多空比{lsar['now']:.2f} 极端"))
        passed += 1
    elif lsar:
        checks.append(("⚠️", f"多空比{lsar['now']:.2f}"))
    else:
        checks.append(("⚠️", "多空比N/A"))

    # Taker卖出
    total += 1
    if taker and taker["now"] < 0.85:
        checks.append(("✅", f"Taker卖>买 {taker['now']:.2f} 恐慌"))
        passed += 1
    elif taker:
        checks.append(("⚠️", f"Taker比 {taker['now']:.2f}"))
    else:
        checks.append(("⚠️", "Taker N/A"))

    # 价格z-score低位
    total += 1
    if zs and zs["price_z"] < -1.5:
        checks.append(("✅", f"价格低位 {zs['price_z']:+.1f}σ"))
        passed += 1
    elif zs:
        checks.append(("⚠️", f"价格z={zs['price_z']:+.1f}"))
    else:
        checks.append(("⚠️", "z-score N/A"))

    return {"symbol": symbol, "passed": passed, "total": total, "checks": checks,
            "price": t24.get("price", 0), "chg": t24.get("chg", 0),
            "vol": t24.get("vol", 0), "rsi": rsi_4h}

def breakout_scan(symbol, kl4h, t24, funding, taker):
    """🚀 突破启动模式"""
    c = [k["c"] for k in kl4h]
    v = vegas_full(kl4h)
    rsi_4h = rsi_val(c, 14)
    atr_4h = atr_val(kl4h, 14)
    zs = z_score_analysis(kl4h)

    checks = []
    passed = 0; total = 0

    # ATR扩张
    total += 1
    atr_prev = atr_val(kl4h[:-20], 14) if len(kl4h) >= 34 else 0
    if atr_prev > 0 and atr_4h / atr_prev > 1.2:
        checks.append(("✅", f"ATR扩张 {atr_4h/atr_prev:.1f}x"))
        passed += 1
    else:
        checks.append(("⚠️", "ATR未扩张"))

    # 放量
    total += 1
    if zs and zs["vol_z"] > 1.5:
        checks.append(("✅", f"放量 {zs['vol_z']:+.1f}σ"))
        passed += 1
    elif zs:
        checks.append(("⚠️", f"量z={zs['vol_z']:+.1f}"))
    else:
        checks.append(("⚠️", "z-score N/A"))

    # 突破EMA
    total += 1
    e144 = ema(c, 144)
    if e144 and c[-1] > e144:
        checks.append(("✅", "价格>EMA144"))
        passed += 1
    elif e144:
        checks.append(("❌", "未突破EMA144"))
    else:
        checks.append(("⚠️", "EMA N/A"))

    # RSI动能
    total += 1
    if 55 < rsi_4h < 80:
        checks.append(("✅", f"RSI {rsi_4h:.0f} 动能"))
        passed += 1
    else:
        checks.append(("⚠️", f"RSI {rsi_4h:.0f}"))

    # Taker买入
    total += 1
    if taker and taker["now"] > 1.2:
        checks.append(("✅", f"Taker买>卖 {taker['now']:.2f}"))
        passed += 1
    elif taker:
        checks.append(("⚠️", f"Taker比 {taker['now']:.2f}"))
    else:
        checks.append(("⚠️", "Taker N/A"))

    # 费率未过热
    total += 1
    if funding is not None and funding < 0.05:
        checks.append(("✅", f"费率{funding:+.4f}% 未过热"))
        passed += 1
    elif funding is not None:
        checks.append(("❌", f"费率{funding:+.4f}% 过热"))
    else:
        checks.append(("⚠️", "费率N/A"))

    # 结构突破
    total += 1
    highs_20 = max(k["h"] for k in kl4h[-30:-10]) if len(kl4h) >= 30 else 0
    if highs_20 > 0 and c[-1] > highs_20:
        checks.append(("✅", "突破前高"))
        passed += 1
    else:
        checks.append(("⚠️", "未突破前高"))

    return {"symbol": symbol, "passed": passed, "total": total, "checks": checks,
            "price": t24.get("price", 0), "chg": t24.get("chg", 0),
            "vol": t24.get("vol", 0), "rsi": rsi_4h}

# ═══════════════════════════════
# K线图
# ═══════════════════════════════
def make_advanced_chart(kl, coin_name, tf_label, vegas_data=None):
    """专业K线图: 蜡烛+EMA+维加斯+成交量"""
    if len(kl) < 10:
        return go.Figure()

    closes = [k["c"] for k in kl]
    highs = [k["h"] for k in kl]
    lows = [k["l"] for k in kl]
    volumes = [k["v"] for k in kl]
    dates = list(range(len(kl)))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.75, 0.25], vertical_spacing=0.03)

    # K线
    fig.add_trace(go.Candlestick(
        x=dates, open=[k["o"] for k in kl], high=highs, low=lows, close=closes,
        name="", increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
        increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350",
    ), row=1, col=1)

    # EMA均线
    for p, color in [(7, "#2962ff"), (25, "#ff6d00"), (99, "#aa00ff")]:
        vals = ema_series(closes, p)
        fig.add_trace(go.Scatter(x=dates, y=vals, name=f"EMA{p}",
                                 line=dict(color=color, width=1),
                                 legendgroup="ma"), row=1, col=1)

    # 维加斯通道
    if vegas_data:
        for p, color in [(144, "#00bfa5"), (169, "#64ffda"), (576, "#ffab00"), (676, "#ff5252")]:
            vals = ema_series(closes, p)
            dash = "solid" if p in (144, 169) else "dot"
            width = 1.5 if p in (144, 169) else 0.8
            fig.add_trace(go.Scatter(x=dates, y=vals, name=f"EMA{p}",
                                     line=dict(color=color, width=width, dash=dash),
                                     legendgroup="vegas"), row=1, col=1)

    # 成交量
    vol_colors = ["#26a69a" if closes[i] >= closes[i - 1] else "#ef5350"
                  for i in range(1, len(closes))]
    vol_colors.insert(0, "#26a69a")
    fig.add_trace(go.Bar(x=dates, y=volumes, name="", marker_color=vol_colors,
                         opacity=0.4, showlegend=False), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", height=450,
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="top", y=1.12, xanchor="left", x=0, font_size=9),
        hovermode="x unified",
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        title=f"{coin_name} · {tf_label}",
    )
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    return fig

# ═══════════════════════════════
# UI
# ═══════════════════════════════
st.set_page_config(page_title="小鹿信息雷达", page_icon="🦌", layout="wide")

# 初始化session
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "scan_time" not in st.session_state:
    st.session_state.scan_time = None
if "scanning" not in st.session_state:
    st.session_state.scanning = False

st.markdown("# 🦌 小鹿信息雷达")
st.caption("客观数据展示 · 不做决策 · 你的判断才是最终决策")

# 侧边栏
with st.sidebar:
    st.header("🔍 全市场扫描")

    scan_range = st.selectbox("扫描范围", ["Top 50 (快速)", "Top 100", "Top 200 (全面)"],
                              index=1)
    limit_map = {"Top 50 (快速)": 50, "Top 100": 100, "Top 200 (全面)": 200}

    if st.button("🚀 开始扫描", type="primary", disabled=st.session_state.scanning,
                 use_container_width=True):
        st.session_state.scanning = True
        st.rerun()

    st.divider()

    # 宏观
    fg_val, fg_label = fetch_fear_greed()
    dxy_val = fetch_dxy()
    st.subheader("🌍 宏观环境")
    c1, c2 = st.columns(2)
    with c1:
        if fg_val:
            emoji = "😱" if fg_val < 30 else "😐" if fg_val < 55 else "😀" if fg_val < 70 else "🤤"
            st.metric("恐惧贪婪", f"{emoji} {fg_val}", delta=fg_label)
    with c2:
        if dxy_val:
            emoji = "✅" if dxy_val < 103 else "⚠️" if dxy_val < 105 else "🔴"
            st.metric("DXY", f"{dxy_val:.1f}", delta="弱美元" if dxy_val < 103 else "强美元")

    st.divider()

    # 币种管理
    st.subheader("📋 监视列表")
    if COINS_FILE.exists():
        coins_raw = [l.strip() for l in COINS_FILE.read_text().split("\n")
                     if l.strip() and not l.strip().startswith("#")]
    else:
        coins_raw = DEFAULT_COINS.strip().split("\n")
        COINS_FILE.parent.mkdir(parents=True, exist_ok=True)
        COINS_FILE.write_text(DEFAULT_COINS)

    coins = [c.upper() for c in coins_raw if c.upper().endswith("USDT")]
    if not coins:
        coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    new_coin = st.text_input("添加币种 (如 DOGEUSDT)", placeholder="BTCUSDT")
    if st.button("➕ 添加"):
        new_sym = new_coin.strip().upper()
        if new_sym.endswith("USDT") and new_sym not in coins:
            coins.append(new_sym)
            COINS_FILE.write_text("\n".join(coins))
            st.success(f"已添加 {new_sym}")
            st.cache_data.clear()
            st.rerun()

    st.caption(f"当前 {len(coins)} 个币种")

    st.divider()
    st.subheader("📊 单币深度分析")
    selected_coin = st.selectbox("选择币种", coins)
    tf_key = st.radio("K线周期", ["5m", "15m", "1h", "4h", "1d"], horizontal=True,
                      index=2)

# ═══════ 扫描逻辑 ═══════
if st.session_state.scanning:
    with st.spinner("🔍 正在扫描全市场..."):
        symbols = fetch_all_symbols()
        limit = limit_map[scan_range]
        symbols = symbols[:limit]
        now_str = datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

        progress = st.progress(0)
        status_text = st.empty()

        sections = {"trend": [], "bottom": [], "breakout": []}

        def scan_one(sym):
            if sym == "BTCUSDT": return None
            try:
                kl4h = fetch_klines(sym, "4h", 600)
                if len(kl4h) < 80: return None
                kl1h = fetch_klines(sym, "1h", 100)
                t24 = fetch_24h(sym)
                funding = fetch_funding(sym)
                lsar = fetch_lsar(sym)
                taker = fetch_taker(sym)
                cvd = fetch_cvd(sym)

                results = []
                t = trend_scan(sym, kl4h, kl1h, t24, funding, lsar, taker, cvd)
                if t and t["passed"] >= max(5, t["total"] // 2):
                    results.append(("trend", t))
                b = bottom_scan(sym, kl4h, t24, funding, lsar, taker)
                if b and b["passed"] >= 4:
                    results.append(("bottom", b))
                bk = breakout_scan(sym, kl4h, t24, funding, taker)
                if bk and bk["passed"] >= 4:
                    results.append(("breakout", bk))
                return results
            except:
                return None

        processed = 0
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = {pool.submit(scan_one, s): s for s in symbols}
            for fut in as_completed(futures):
                processed += 1
                if processed % 10 == 0:
                    progress.progress(min(processed / len(symbols), 1.0))
                    status_text.text(f"已扫描 {processed}/{len(symbols)}...")
                try:
                    results = fut.result(timeout=25)
                    if results:
                        for mode, item in results:
                            sections[mode].append(item)
                except:
                    pass

        for mode in sections:
            sections[mode].sort(key=lambda x: (x["passed"] / max(1, x["total"]), x["vol"]),
                               reverse=True)
            sections[mode] = sections[mode][:8]

        st.session_state.scan_results = sections
        st.session_state.scan_time = now_str
        st.session_state.scanning = False
        progress.empty()
        status_text.empty()
        st.rerun()

# ═══════ 主面板 ═══════
tab1, tab2, tab3, tab4 = st.tabs(["📊 单币分析", "📋 扫描结果", "📰 新闻", "💹 费率"])

# Tab1: 单币分析
with tab1:
    c1, c2, c3, c4, c5 = st.columns(5)
    ticker = fetch_24h(selected_coin)
    funding = fetch_funding(selected_coin)
    kl = fetch_klines(selected_coin, tf_key, 200)
    vd = vegas_full(kl) if len(kl) >= 600 else None
    hmm = hmm_analyze(kl)
    zs = z_score_analysis(kl)
    rsi_4h = rsi_val([k["c"] for k in kl], 14)
    atr_4h = atr_val(kl, 14)
    lsar = fetch_lsar(selected_coin)
    taker = fetch_taker(selected_coin)
    cvd = fetch_cvd(selected_coin)

    price = ticker.get("price", 0)
    chg = ticker.get("chg", 0)
    chg_sign = "+" if chg >= 0 else ""

    with c1: st.metric("价格", f"${price:,.4f}", delta=f"{chg_sign}{chg:.2f}%")
    with c2: st.metric("24H量", f"${ticker.get('vol', 0)/1e6:,.0f}M")
    with c3:
        f_str = f"{funding:+.4f}%" if funding is not None else "N/A"
        f_delta = "空头拥挤" if (funding and funding < -0.01) else ("多头过热" if (funding and funding > 0.05) else None)
        st.metric("资金费率", f_str, delta=f_delta, delta_color="inverse" if f_delta else "normal")
    with c4:
        st.metric("RSI", f"{rsi_4h:.0f}",
                  delta="超买" if rsi_4h > 70 else ("超卖" if rsi_4h < 30 else None))
    with c5:
        st.metric("HMM", hmm.get("regime", "?"))
    
    # 指标行
    ic1, ic2, ic3, ic4, ic5, ic6, ic7 = st.columns(7)
    with ic1:
        lsar_str = f"{lsar['now']:.2f}" if lsar else "N/A"
        lsar_d = "↑" if lsar and lsar["trend"] == "up" else "↓"
        st.caption(f"多空比 {lsar_str} {lsar_d}")
    with ic2:
        taker_str = f"{taker['now']:.2f}" if taker else "N/A"
        st.caption(f"Taker {taker_str}")
    with ic3:
        cvd_str = f"{cvd:+,.0f}" if cvd else "N/A"
        st.caption(f"CVD {cvd_str}")
    with ic4:
        v_str = vd["state"] if vd else "N/A"
        st.caption(f"维加斯 {v_str}")
    with ic5:
        if zs:
            st.caption(f"z-score {zs['total_abs']}")
            if zs["anomalies"]:
                st.caption(f"⚠️ {zs['anomalies'][0]}")
    with ic6:
        st.caption(f"ATR {atr_4h:.4f}")
    with ic7:
        e50 = ema([k["c"] for k in kl], 50)
        dev = (price - e50) / e50 * 100 if e50 else 0
        st.caption(f"vsEMA50 {dev:+.1f}%")

    # K线图
    fig = make_advanced_chart(kl, selected_coin.replace("USDT", "/USDT"), tf_key, vd)
    st.plotly_chart(fig, use_container_width=True)

# Tab2: 扫描结果
with tab2:
    if st.session_state.scan_results and st.session_state.scan_time:
        st.success(f"📡 扫描时间: {st.session_state.scan_time}")
        section_data = st.session_state.scan_results

        mode_tabs = st.tabs([
            f"📈 趋势追踪 ({len(section_data['trend'])}候选)",
            f"🔄 触底反弹 ({len(section_data['bottom'])}候选)",
            f"🚀 突破启动 ({len(section_data['breakout'])}候选)",
        ])

        mode_names = ["trend", "bottom", "breakout"]

        for i, mode_key in enumerate(mode_names):
            with mode_tabs[i]:
                items = section_data[mode_key]
                if not items:
                    st.info("本模式暂无候选")
                else:
                    for item in items:
                        pct = item["passed"] / max(1, item["total"]) * 100
                        bar_color = "#26a69a" if pct >= 70 else "#ff9800" if pct >= 50 else "#ef5350"
                        chg_str = f"+{item['chg']:.1f}%" if item['chg'] >= 0 else f"{item['chg']:.1f}%"
                        chg_color = "#26a69a" if item['chg'] >= 0 else "#ef5350"

                        with st.container():
                            cols = st.columns([1, 1, 2, 1])
                            with cols[0]:
                                sym_clean = item["symbol"].replace("USDT", "")
                                st.markdown(f"### {sym_clean}/USDT")
                            with cols[1]:
                                st.metric("价格", f"${item['price']:,.4f}",
                                          delta=chg_str, delta_color="normal")
                            with cols[2]:
                                # 通过率条
                                st.progress(pct / 100, text=f"{item['passed']}/{item['total']} 通过")
                            with cols[3]:
                                st.caption(f"量 ${item['vol']/1e6:,.0f}M")
                                st.caption(f"RSI {item.get('rsi', 'N/A'):.0f}")

                            # 检查项
                            check_cols = st.columns(4)
                            for j, (mark, text) in enumerate(item["checks"]):
                                with check_cols[j % 4]:
                                    c = "#26a69a" if "✅" in mark else ("#ef5350" if "❌" in mark else "#ff9800")
                                    st.markdown(f'<span style="color:{c};font-size:13px">{mark} {text}</span>',
                                                unsafe_allow_html=True)
                            st.divider()
    else:
        st.info("👈 点击左侧「开始扫描」按钮，扫描全市场")
        st.caption("扫描200个USDT合约，判断趋势/触底/突破三种模式")

# Tab3: 新闻
with tab3:
    news = fetch_news(20)
    for n in news:
        badge = "🔴" if n.get("rel", 0) >= 2 else "⚪"
        st.markdown(f"{badge} **[{n['source']}]** {n['title'][:120]}")

# Tab4: 费率总览
with tab4:
    fcols = st.columns(2)
    rates = []
    for coin in coins:
        f = fetch_funding(coin)
        if f is not None:
            rates.append((coin.replace("USDT", ""), f))
    rates.sort(key=lambda x: x[1])

    for i, (name, rate) in enumerate(rates):
        color = "#26a69a" if -0.005 <= rate <= 0.015 else ("#ff9800" if -0.01 <= rate <= 0.03 else "#ef5350")
        with fcols[i % 2]:
            st.metric(name, f"{rate:+.4f}%",
                      delta="空头拥挤" if rate < -0.01 else ("多头过热" if rate > 0.05 else None),
                      delta_color="inverse")

# ═══════ 页脚 ═══════
st.divider()
st.caption(f"🦌 小鹿信息雷达 v4 · {datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')} · "
           "只做信息展示不做交易建议 · 数据来源: Binance API")

# 自动刷新
if st.session_state.get("auto_refresh", True):
    time.sleep(300)
    st.rerun()
