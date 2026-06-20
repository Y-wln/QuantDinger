"""Volume analysis - surges, taker volume, HVN/LVN."""
def volume_surge(klines, recent_n=3, avg_n=12):
    """Detect volume surge. Returns (ratio, direction_sign)."""
    if len(klines) < avg_n:
        return 1, 0
    vols = [float(k['v']) for k in klines]
    avg = sum(vols[-avg_n:]) / avg_n
    recent = sum(vols[-recent_n:]) / recent_n
    ratio = recent / avg if avg > 0 else 1
    closes = [float(k['c']) for k in klines]
    recent_chg = (closes[-1] - closes[-recent_n]) / closes[-recent_n] * 100 if len(closes) >= recent_n else 0
    return ratio, 1 if recent_chg > 1 else (-1 if recent_chg < -1 else 0)

def score_volume_surge(klines):
    """Score volume surge. Returns (score, reason, is_leading)."""
    ratio, direction = volume_surge(klines)
    if ratio > 2.0:
        if direction > 0:
            return 6, f'+6 放量上涨 vol_x{ratio:.1f}', True
        elif direction < 0:
            return -6, f'-6 放量下跌 vol_x{ratio:.1f}', True
        else:
            return 0, f'放量震荡 vol_x{ratio:.1f}', False
    return 0, None, False

def atr(klines, period=14):
    """Calculate ATR."""
    if len(klines) < period + 1:
        return 0
    trs = []
    highs = [float(k['h']) for k in klines]
    lows = [float(k['l']) for k in klines]
    closes = [float(k['c']) for k in klines]
    for i in range(1, len(klines)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i] - closes[i-1]))
        trs.append(tr)
    return sum(trs[-period:]) / period

def score_atr_volatility(klines):
    """Score ATR-based volatility. Returns (score, reason)."""
    val = atr(klines)
    if val <= 0:
        return 0, None
    current = float(klines[-1]['c'])
    pct = val / current * 100
    if pct > 5:
        return 3, f'+3 超高波动(ATR:{pct:.1f}%)'
    elif pct < 1:
        return 0, f'低波动(ATR:{pct:.1f}%)'
    return 0, None
