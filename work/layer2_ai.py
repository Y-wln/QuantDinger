#!/usr/bin/env python3
"""小鹿 Layer2 AI分析 v4 — 全周期管道 + CVD/OI/订单流 + 7维度AI"""

import os, sys, json, math, time
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
import requests, numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path

BJT = timezone(timedelta(hours=8))
B, BF = "https://api.binance.com", "https://fapi.binance.com"
API, KEY = "https://api.deepseek.com/v1/chat/completions", "sk-df5444cb6e414716bbea7316ce5e35a7"
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0"})
S.proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

def fetch(url, t=8):
    try: return S.get(url, timeout=t).json()
    except: return None

def klines(sym, iv, lim):
    d = fetch(f"{B}/api/v3/klines?symbol={sym}&interval={iv}&limit={lim}")
    return [{"o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "v": float(k[5])} for k in d] if d else []

def ticker(sym):
    r = fetch(f"{B}/api/v3/ticker/24hr?symbol={sym}")
    return {"price": float(r["lastPrice"]), "chg": float(r["priceChangePercent"]),
            "vol": float(r["quoteVolume"]), "high": float(r["highPrice"]), "low": float(r["lowPrice"])} if r else {}

def funding(sym):
    r = fetch(f"{BF}/fapi/v1/premiumIndex?symbol={sym}")
    return float(r["lastFundingRate"]) * 100 if r else None

def oi_data(sym):
    """OI + OI变化率"""
    now = fetch(f"{BF}/fapi/v1/openInterest?symbol={sym}")
    hist = fetch(f"{BF}/futures/data/openInterestHist?symbol={sym}&period=5m&limit=12")
    if not now or not hist: return None
    cur_oi = float(now["openInterest"])
    prev_oi = float(hist[0].get("sumOpenInterest", cur_oi))
    chg_5m = (cur_oi - prev_oi) / prev_oi * 100
    # 1h change
    if len(hist) >= 12:
        oi_1h_ago = float(hist[-1].get("sumOpenInterest", cur_oi))
        chg_1h = (cur_oi - oi_1h_ago) / oi_1h_ago * 100
    else:
        chg_1h = chg_5m * 12
    return {
        "当前OI": f"${cur_oi/1e6:.1f}M",
        "5分变化": f"{chg_5m:+.2f}%",
        "1时变化": f"{chg_1h:+.2f}%",
        "趋势": "OI增长" if chg_1h > 0.5 else ("OI下降" if chg_1h < -0.5 else "OI平稳")
    }

def cvd(sym, limit=200):
    """累积成交量差 — 买卖压力"""
    trades = fetch(f"{B}/api/v3/aggTrades?symbol={sym}&limit={limit}")
    if not trades: return None
    cvd_val, buy_vol, sell_vol = 0, 0, 0
    for t in trades:
        q = float(t["q"])
        if t.get("m", False):
            cvd_val -= q; sell_vol += q
        else:
            cvd_val += q; buy_vol += q
    total = buy_vol + sell_vol
    return {
        "CVD": f"{cvd_val:+,.0f}",
        "主动买入量": f"{buy_vol:.0f}",
        "主动卖出量": f"{sell_vol:.0f}",
        "买卖比": round(buy_vol / sell_vol, 2) if sell_vol > 0 else 1,
        "方向": "买方主导" if cvd_val > 0 else "卖方主导"
    }

def lsar(sym):
    d = fetch(f"{BF}/futures/data/globalLongShortAccountRatio?symbol={sym}&period=5m&limit=4")
    if not d: return None
    r = [float(x["longShortRatio"]) for x in d]
    return {"now": r[-1], "trend": "多头增" if r[-1] > r[-3] else "空头增"}

def taker_ratio(sym):
    d = fetch(f"{BF}/futures/data/takerlongshortRatio?symbol={sym}&period=5m&limit=4")
    if not d: return None
    r = [float(x["buySellRatio"]) for x in d]
    return {"now": r[-1], "trend": "主动买入" if r[-1] > r[-3] else "主动卖出"}

def top_lsr(sym):
    """顶级交易员多空比"""
    d = fetch(f"{BF}/futures/data/topLongShortAccountRatio?symbol={sym}&period=5m&limit=4")
    if not d: return None
    r = [float(x["longShortRatio"]) for x in d]
    return {"now": r[-1], "trend": "多头增" if r[-1] > r[-3] else "空头增"}

def fg_idx():
    r = fetch("https://api.alternative.me/fng/?limit=1")
    return {"value": int(r["data"][0]["value"]), "label": r["data"][0]["value_classification"]} if r else None

def dxy_idx():
    r = fetch("https://api.alternative.me/dxy/")
    return float(r["dxy"]) if r and "dxy" in r else None

def fetch_news():
    kw = ["crypto", "bitcoin", "ethereum", "solana", "btc", "eth", "sol",
          "fed", "sec", "regulation", "etf", "tariff", "hack",
          "加密", "比特币", "以太坊", "区块链", "币", "合约", "监管", "加息", "降息", "鲸鱼", "爆仓"]
    items = []
    try:
        r = requests.get("https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        if r and "data" in r:
            for d in r["data"].get("roll_data", [])[:30]:
                t = d.get("title", "") or d.get("brief", "")
                if t and any(k in t.lower() for k in kw):
                    items.append(f"[财联社] {t[:80]}")
    except: pass
    try:
        r = requests.get("https://api.theblockbeats.info/v1/newsflash/list?page=1&limit=10",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=5).json()
        if r and "data" in r:
            for d in r["data"].get("list", [])[:10]:
                t = d.get("title", "") or d.get("content", "")
                if t: items.append(f"[BlockBeats] {t[:80]}")
    except: pass
    return items[:8]

def small_tf_pipeline(sym):
    """小级别入场管道: 5m/15m 完整分析"""
    result = {}
    for tf in ["15m", "5m"]:
        kl = klines(sym, tf, 100)
        if len(kl) < 30: continue
        c = [k["c"] for k in kl]; v = [k["v"] for k in kl]
        h = [k["h"] for k in kl]; l = [k["l"] for k in kl]

        # 趋势方向
        e20 = sum(c[-20:]) / 20; e50 = sum(c[-50:]) / 50 if len(c) >= 50 else e20
        trend = "上升" if c[-1] > e20 > e50 else ("下降" if c[-1] < e20 < e50 else "震荡")

        # RSI
        r = 50
        if len(c) >= 15:
            ch = [c[i] - c[i - 1] for i in range(1, len(c))]
            ag = sum(x for x in ch[-14:] if x > 0) / 14
            al = sum(-x for x in ch[-14:] if x < 0) / 14
            r = 50 if al == 0 else 100 - 100 / (1 + ag / al)

        # 放量/缩量
        avg_v = np.mean(v[:-5]) if len(v) > 10 else np.mean(v)
        last_v = sum(v[-3:]) / 3
        vol_ratio = last_v / avg_v if avg_v > 0 else 1

        # 波动
        atr_now = max(h[-5:]) - min(l[-5:]) if len(h) >= 5 else 0

        # 价格动量
        chg = (c[-1] - c[-6]) / c[-6] * 100 if len(c) >= 6 else 0

        # 综合小级别信号
        if trend == "上升" and r > 55 and vol_ratio > 1.2 and chg > 0:
            signal = "🔴 多头启动信号"
        elif trend == "下降" and r < 45 and vol_ratio > 1.2 and chg < 0:
            signal = "🔵 空头启动信号"
        elif vol_ratio < 0.7 and abs(chg) < 0.3:
            signal = "⏸ 缩量盘整"
        else:
            signal = "➡ 常态波动"

        result[tf] = {
            "趋势": trend,
            "RSI": round(r, 1),
            "量比": f"{vol_ratio:.1f}x",
            "3根量": f"{last_v:.0f}",
            "ATR": f"{atr_now:.2f}",
            "6根涨跌": f"{chg:+.2f}%",
            "综合信号": signal
        }
    return result

# ═══════════ 指标 ═══════════
def ema(v, p):
    if len(v) < p: return None
    k = 2 / (p + 1); r = v[0]
    for x in v[1:]: r = x * k + r * (1 - k)
    return r

def rsi_val(c, p=14):
    if len(c) < p + 1: return 50
    ch = [c[i] - c[i - 1] for i in range(1, len(c))]
    ag = sum(x for x in ch[:p] if x > 0) / p; al = sum(-x for x in ch[:p] if x < 0) / p
    if al == 0: return 100
    for i in range(p, len(ch)):
        x = ch[i]; ag = (ag * (p - 1) + max(x, 0)) / p; al = (al * (p - 1) + max(-x, 0)) / p
    return 50 if al == 0 else 100 - 100 / (1 + ag / al)

def vegas_full(c):
    """多周期维加斯"""
    if len(c) < 676: return {}
    result = {}
    for name, per in [("EMA12", 12), ("EMA144", 144), ("EMA169", 169), ("EMA576", 576), ("EMA676", 676)]:
        result[name] = ema(c, per)
    e144, e169, e576, e676 = result["EMA144"], result["EMA169"], result["EMA576"], result["EMA676"]
    cur = c[-1]
    if cur > e144 > e169 and e144 > e576 and e169 > e676: d = "强势多头"
    elif cur > e144 > e169: d = "多头"
    elif cur < e144 < e169 and e144 < e576 and e169 < e676: d = "强势空头"
    elif cur < e144 < e169: d = "空头"
    else: d = "震荡"
    result["方向"] = d
    result["价格vsEMA144"] = f"{(cur - e144) / e144 * 100:+.1f}%"
    result["通道宽度"] = f"{(e169 - e144) / e144 * 100:+.2f}%"
    return result

# ═══════════ 提示词 ═══════════
SYSTEM_PROMPT = """你是加密市场量化分析助手。基于多维数据输出结构化市场分析，帮助用户判断。

【你可以做的】
- 基于数据指出市场偏多/偏空
- 分析多空力量对比（CVD/订单流/OI）
- 指出各维度信号一致性
- 分析全周期管道：大周期定方向 → 中周期等时机 → 小级别找入场

【严格禁止】
- "建议买入""建议卖出""立即入场""应该离场"
- 具体仓位和止损止盈
- "我推荐""你应该"
- 编造数据

【8维度分析】
1. 大周期趋势(25%): 维加斯周线/日线/4H方向 + EMA排列
2. 动量(15%): RSI_4H/1H + 布林带位置
3. 订单流资金(25%): CVD买卖压力 + OI变化 + 多空比 + 顶级交易员 + Taker + 费率
4. 宏观(10%): 恐惧贪婪 + DXY
5. 新闻情绪(10%): 近期新闻倾向
6. 小级别入场(10%): 15m/5m趋势+量价信号+RSI+ATR
7. 多周期一致性(5%): 周→日→4H→1H→15m→5m 方向对比
8. 异常检测: CVD背离、OI与价格背离、极端费率等

【输出格式】
### 市场状态总结
(2-3句)

### 方向判断
- 综合偏向: 偏多/偏空/中性
- 置信度: 高/中/低

### 全周期管道分析
| 周期 | 方向 | 关键数据 |
|------|------|----------|
| 周线/日线 | | |
| 4H | | |
| 1H | | |
| 15m/5m | | |

### 订单流资金分析
- CVD: [数据+解读]
- OI: [数据+解读]
- 多空力量: [综合分析]

### 小级别入场信号
- 15m信号: [...]
- 5m信号: [...]
- 入场条件是否满足: [多周期一致 + 小级别放量 + CVD确认]

### 异常与风险
- 异常: [...]
- 风险: [...]
- 不确定性: 低/中/高

只输出以上部分。"""

# ═══════════ MAIN ═══════════
sym = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"

print(f"[{datetime.now(BJT).strftime('%H:%M:%S')}] 采集全周期数据...")

# 大周期
kl_w = klines(sym, "1w", 100)
kl_d = klines(sym, "1d", 300)
kl_4h = klines(sym, "4h", 700)
kl_1h = klines(sym, "1h", 200)
t = ticker(sym); f = funding(sym)
oi = oi_data(sym); cvd_data = cvd(sym)
ls = lsar(sym); tk = taker_ratio(sym); top = top_lsr(sym)
fg = fg_idx(); dx = dxy_idx(); news = fetch_news()
stf = small_tf_pipeline(sym)

# 指标计算
v_w = vegas_full([k["c"] for k in kl_w]) if len(kl_w) >= 200 else {}
v_d = vegas_full([k["c"] for k in kl_d]) if len(kl_d) >= 200 else {}
v_4h = vegas_full([k["c"] for k in kl_4h])
c4 = [k["c"] for k in kl_4h]; c1 = [k["c"] for k in kl_1h]
r_4h = rsi_val(c4); r_1h = rsi_val(c1)

# 资金费率趋势
funding_trend = "偏多(多头付费)" if f and f > 0.01 else ("偏空(空头付费)" if f and f < -0.01 else "中性")

data = {
    "币种": sym, "时间": datetime.now(BJT).strftime("%Y-%m-%d %H:%M"),
    "价格": f"${t.get('price', 0):,}", "24H涨跌": f"{t.get('chg', 0):+.1f}%",
    "24H量": f"${t.get('vol', 0)/1e9:.2f}B",
    "全周期趋势": {
        "周线": v_w.get("方向", "?"),
        "日线": v_d.get("方向", "?"),
        "4H": v_4h.get("方向", "?"),
        "价格vsEMA144_4H": v_4h.get("价格vsEMA144", "?"),
        "通道宽度": v_4h.get("通道宽度", "?"),
    },
    "动量指标": {"RSI_4H": round(r_4h, 1), "RSI_1H": round(r_1h, 1),
                  "EMA排列_4H": "金叉" if ema(c4, 20) and ema(c4, 50) and ema(c4, 20) > ema(c4, 50) else "死叉"},
    "订单流资金": {
        "CVD": cvd_data,
        "OI": oi,
        "资金费率": f"{f:+.4f}% ({funding_trend})" if f else "N/A",
        "多空比(散户)": f"{ls['now']:.2f} ({ls['trend']})" if ls else "N/A",
        "顶级交易员多空比": f"{top['now']:.2f} ({top['trend']})" if top else "N/A",
        "Taker买卖比": f"{tk['now']:.2f} ({tk['trend']})" if tk else "N/A",
    },
    "宏观": {"恐惧贪婪": f"{fg['value']}({fg['label']})" if fg else "N/A", "DXY": dx},
    "小级别入场信号": stf,
    "新闻": news[:6],
}

user_prompt = f"以下是当前全周期+订单流数据。请按8维度逐项分析。\n\n{json.dumps(data, ensure_ascii=False, indent=2)}"

print(f"[{datetime.now(BJT).strftime('%H:%M:%S')}] 调用DeepSeek 8维度分析...")
body = {"model": "deepseek-chat", "messages": [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": user_prompt}
], "temperature": 0.3, "max_tokens": 2500}

r = requests.post(API,
    data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json; charset=utf-8"},
    timeout=120)

result = r.json()
if "choices" not in result:
    print(f"API错误: {result}"); sys.exit(1)

ai_report = result["choices"][0]["message"]["content"]

print(f"\n{'='*60}")
print(ai_report)
print(f"{'='*60}")

Path.home().joinpath("radar/ai_report.txt").write_text(ai_report, encoding="utf-8")
print(f"\n报告已存: ~/radar/ai_report.txt")
print(f"访问: http://124.221.104.66:8080/ai_report.txt  (先开http.server)")