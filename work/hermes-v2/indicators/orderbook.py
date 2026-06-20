"""Orderbook imbalance + Tape pressure + Taker Volume estimation."""
from indicators import cvd

def estimate_orderbook(kline):
    """Estimate orderbook imbalance from candle structure.
    Returns (score, reason) or (0, None)."""
    o, h, l, c = float(kline['o']), float(kline['h']), float(kline['l']), float(kline['c'])
    body = abs(c - o)
    upper_wick = h - max(c, o)
    lower_wick = min(c, o) - l
    if body == 0:
        return 0, None
    if upper_wick > body * 2:
        return -3, '-3 上影卖压(盘口推算)'
    elif lower_wick > body * 2:
        return 3, '+3 下影买盘(盘口推算)'
    return 0, None

def estimate_tape(klines):
    """Estimate tape pressure from volume+price sequence.
    Returns (score, reason) or (0, None)."""
    if len(klines) < 2:
        return 0, None
    last = klines[-1]
    prev = klines[-2]
    vol_last = float(last['v'])
    vol_prev = float(prev['v'])
    price_up = float(last['c']) > float(prev['c'])
    if vol_last > vol_prev * 1.5:
        if price_up:
            return 3, '+3 放量上涨(tape推算)'
        else:
            return -3, '-3 放量下跌(tape推算)'
    return 0, None

def taker_volume_ratio(klines, recent_n=5):
    """Estimate taker buy/sell ratio from kline data.
    Positive close with high vol = taker buy dominance."""
    if len(klines) < recent_n:
        return 0.5
    buy_vol = 0
    sell_vol = 0
    for k in klines[-recent_n:]:
        v = float(k['v'])
        if float(k['c']) > float(k['o']):
            buy_vol += v
        else:
            sell_vol += v
    total = buy_vol + sell_vol
    if total == 0:
        return 0.5
    return round(buy_vol / total, 2)

def score_taker_volume(klines):
    """Score taker volume ratio. Returns (score, reason)."""
    ratio = taker_volume_ratio(klines)
    if ratio > 0.65:
        return 4, f'+4 主动买盘主导({int(ratio*100)}%)'
    elif ratio < 0.35:
        return -4, f'-4 主动卖盘主导({int(ratio*100)}%)'
    return 0, None

def score_orderbook_tape(klines_1h):
    """Combined orderbook + tape scoring. Returns list of (score, reason, is_leading)."""
    results = []
    if klines_1h and len(klines_1h) >= 2:
        s, r = estimate_orderbook(klines_1h[-1])
        if r:
            results.append((s, r, False))
        s, r = estimate_tape(klines_1h)
        if r:
            results.append((s, r, False))
        s, r = score_taker_volume(klines_1h)
        if r:
            results.append((s, r, False))
    return results
