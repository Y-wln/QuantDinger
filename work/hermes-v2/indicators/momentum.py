"""Momentum scoring across multiple timeframes."""
def momentum_score(klines, periods=None):
    """Multi-period momentum. Returns aggregate score -20 to +20."""
    if periods is None:
        periods = [6, 12, 24]
    if len(klines) < max(periods):
        return 0
    closes = [float(k['c']) for k in klines]
    total = 0
    for p in periods:
        if len(closes) > p:
            chg = (closes[-1] - closes[-p]) / closes[-p] * 100
            if chg > 2:
                total += 8
            elif chg > 0.5:
                total += 4
            elif chg < -2:
                total -= 8
            elif chg < -0.5:
                total -= 4
    return max(-20, min(20, total))

def score_momentum(klines):
    """Score momentum. Returns (score, reason, is_leading)."""
    mom = momentum_score(klines)
    if mom >= 20:
        return 6, '+6 动量加速', True
    elif mom <= -20:
        return -6, '-6 动量减速', True
    elif mom >= 10:
        return 3, '+3 动量偏多', False
    elif mom <= -10:
        return -3, '-3 动量偏空', False
    return 0, None, False

def detect_pin_bar(klines, idx=-1):
    """Detect pin bar at index. Returns 'bullish_pin'|'bearish_pin'|None."""
    if len(klines) < abs(idx):
        return None
    k = klines[idx]
    o, h, l, c = float(k['o']), float(k['h']), float(k['l']), float(k['c'])
    body = abs(c - o)
    upper_wick = h - max(c, o)
    lower_wick = min(c, o) - l
    if body == 0:
        return None
    if lower_wick > body * 2 and upper_wick < body * 0.5:
        return 'bullish_pin'
    if upper_wick > body * 2 and lower_wick < body * 0.5:
        return 'bearish_pin'
    return None

def detect_doji(klines, idx=-1):
    """Detect doji. Returns 'dragonfly'|'gravestone'|None."""
    if len(klines) < abs(idx):
        return None
    k = klines[idx]
    o, h, l, c = float(k['o']), float(k['h']), float(k['l']), float(k['c'])
    body = abs(c - o)
    total_range = h - l
    if total_range == 0:
        return None
    if body < total_range * 0.1:
        if (c - l) > (h - c) * 2:
            return 'dragonfly_doji'
        elif (h - c) > (c - l) * 2:
            return 'gravestone_doji'
    return None

def score_rejection(klines):
    """Score candle rejection patterns. Returns list of (score, reason)."""
    results = []
    pb = detect_pin_bar(klines)
    if pb == 'bullish_pin':
        results.append((3, '+3 看涨影线'))
    elif pb == 'bearish_pin':
        results.append((-3, '-3 看跌影线'))
    dj = detect_doji(klines)
    if dj == 'dragonfly_doji':
        results.append((2, '+2 蜻蜓十字'))
    elif dj == 'gravestone_doji':
        results.append((-2, '-2 墓碑十字'))
    return results
