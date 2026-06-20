"""Market structure detection - trend, SMC, regime."""
def detect_structure(klines, ma_period=20):
    """Detect trend structure: up/down/neutral with confidence."""
    if len(klines) < ma_period:
        return 'neutral', 0
    closes = [float(k['c']) for k in klines]
    ma = sum(closes[-ma_period:]) / ma_period
    current = closes[-1]
    # Simple trend: price vs MA + recent slope
    recent_slope = (closes[-1] - closes[-5]) / closes[-5] * 100 if len(closes) >= 5 else 0
    if current > ma * 1.02 and recent_slope > 0.5:
        return 'up', 3
    elif current < ma * 0.98 and recent_slope < -0.5:
        return 'down', 3
    elif current > ma:
        return 'up', 1
    elif current < ma:
        return 'down', 1
    return 'neutral', 0

def detect_bos_choch(klines):
    """Detect Break of Structure / Change of Character (SMC)."""
    if len(klines) < 30:
        return {'structure': 'neutral'}
    highs = [float(k['h']) for k in klines]
    lows = [float(k['l']) for k in klines]
    closes = [float(k['c']) for k in klines]
    # Find recent swing highs/lows
    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])
    current = closes[-1]
    prev_high = max(highs[-40:-20]) if len(highs) >= 40 else recent_high
    prev_low = min(lows[-40:-20]) if len(lows) >= 40 else recent_low
    if current > prev_high:
        return {'structure': 'bullish'}
    elif current < prev_low:
        return {'structure': 'bearish'}
    elif current > recent_high * 0.98:
        return {'structure': 'bullish'}
    elif current < recent_low * 1.02:
        return {'structure': 'bearish'}
    return {'structure': 'neutral'}

def regime_amplifier(struct4, struct1, score):
    """Amplify scores aligned with trend, dampen counter-trend."""
    bonus = 0
    reason = None
    if struct4 == 'down' and struct1 == 'down':
        if score < 0:
            bonus = -6; reason = '-6 趋势下跌(做空放大)'
        elif score > 0:
            bonus = -4; reason = '-4 逆趋势做多(衰减)'
    elif struct4 == 'up' and struct1 == 'up':
        if score > 0:
            bonus = 6; reason = '+6 趋势上涨(做多放大)'
        elif score < 0:
            bonus = 4; reason = '+4 逆趋势做空(衰减)'
    elif struct4 == 'down':
        if score < 0:
            bonus = -3; reason = '-3 4h下跌偏空'
        elif score > 0:
            bonus = -2; reason = '-2 4h下跌逆势'
    elif struct4 == 'up':
        if score > 0:
            bonus = 3; reason = '+3 4h上涨偏多'
        elif score < 0:
            bonus = 2; reason = '+2 4h上涨逆势'
    return bonus, reason

def score_structure(k4, k1):
    """Score 4h + 1h structure. Returns list of (score, reason)."""
    results = []
    s4, c4 = detect_structure(k4)
    s1, c1 = detect_structure(k1)
    if s4 == 'up':
        results.append((3, '+3 4h up'))
    elif s4 == 'down':
        results.append((-3, '-3 4h down'))
    if s1 == 'up':
        results.append((2, '+2 1h up'))
    elif s1 == 'down':
        results.append((-2, '-2 1h down'))
    smc = detect_bos_choch(k4)
    if smc['structure'] == 'bullish':
        results.append((2, '+2 SMC bullish'))
    elif smc['structure'] == 'bearish':
        results.append((-2, '-2 SMC bearish'))
    return results, s4, s1
