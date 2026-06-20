"""Candle patterns: engulfing, pin bar, doji."""
def detect_engulfing(klines):
    """Detect bullish/bearish engulfing patterns.
    Bullish: red candle followed by green candle that fully engulfs it.
    Bearish: green candle followed by red candle that fully engulfs it."""
    if len(klines) < 2:
        return None
    k1 = klines[-2]
    k2 = klines[-1]
    o1, c1 = float(k1['o']), float(k1['c'])
    o2, c2 = float(k2['o']), float(k2['c'])
    # Bullish engulfing: k1 red, k2 green, k2 body engulfs k1 body
    if c1 < o1 and c2 > o2:
        if o2 <= c1 and c2 >= o1:
            return 'bullish_engulfing'
    # Bearish engulfing: k1 green, k2 red, k2 body engulfs k1 body
    if c1 > o1 and c2 < o2:
        if o2 >= c1 and c2 <= o1:
            return 'bearish_engulfing'
    return None

def detect_pin_bar(klines, idx=-1):
    """Detect pin bar (long wick, small body)."""
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
    """Detect doji (tiny body)."""
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
        return 'doji'
    return None

def score_engulfing(klines):
    """Score engulfing patterns. Returns list of (score, reason)."""
    results = []
    eng = detect_engulfing(klines)
    if eng == 'bullish_engulfing':
        results.append((8, '+8 看涨吞没'))
    elif eng == 'bearish_engulfing':
        results.append((-8, '-8 看跌吞没'))
    return results

def score_rejection(klines):
    """Score pin bar + doji patterns. Returns list of (score, reason)."""
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
