"""MACD indicator."""
def ema(values, period):
    if len(values) < period:
        return values[-1] if values else 0
    k = 2 / (period + 1)
    result = sum(values[:period]) / period
    for v in values[period:]:
        result = v * k + result * (1 - k)
    return result

def macd(closes, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram)."""
    if len(closes) < slow + signal:
        return 0, 0, 0
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line = fast_ema - slow_ema
    # Approximate signal line
    signal_line = macd_line * 0.8  # simplified
    hist = macd_line - signal_line
    return round(macd_line, 4), round(signal_line, 4), round(hist, 4)

def score_macd(closes):
    """Score MACD. Returns (score, reason)."""
    md, mdea, mh = macd(closes)
    if md > mdea and mh > 0:
        return 3, '+3 MACD golden'
    elif md < mdea and mh < 0:
        return -3, '-3 MACD dead'
    return 0, None

def adx(klines, period=14):
    """Calculate ADX - trend strength."""
    if len(klines) < period + 1:
        return 0
    highs = [float(k['h']) for k in klines]
    lows = [float(k['l']) for k in klines]
    closes = [float(k['c']) for k in klines]
    tr_list = []
    plus_dm = []
    minus_dm = []
    for i in range(1, len(klines)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i] - closes[i-1]))
        tr_list.append(tr)
        up = highs[i] - highs[i-1]
        down = lows[i-1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
    atr_val = sum(tr_list[-period:]) / period
    plus_di = (sum(plus_dm[-period:]) / period) / atr_val * 100 if atr_val > 0 else 0
    minus_di = (sum(minus_dm[-period:]) / period) / atr_val * 100 if atr_val > 0 else 0
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
    return round(dx, 1)

def score_adx(klines, current_score):
    """Score ADX trend strength. Returns (score, reason)."""
    val = adx(klines)
    if val > 40:
        return (5 if current_score > 0 else -5), f'+5 强趋势(ADX>40)'
    elif val > 25:
        return (2 if current_score > 0 else -2), f'+2 中等趋势(ADX>25)'
    return 0, f'ADX{val}(弱趋势)'

def supertrend(klines, period=10, multiplier=3.0):
    """SuperTrend. Returns ('long'|'short', value)."""
    if len(klines) < period:
        return 'neutral', 0
    highs = [float(k['h']) for k in klines]
    lows = [float(k['l']) for k in klines]
    closes = [float(k['c']) for k in klines]
    atr_val = sum(max(highs[i] - lows[i],
                      abs(highs[i] - closes[i-1]),
                      abs(lows[i] - closes[i-1]))
                  for i in range(1, len(klines))) / (len(klines) - 1)
    basic_upper = (max(highs[-period:]) + min(lows[-period:])) / 2 + multiplier * atr_val
    basic_lower = (max(highs[-period:]) + min(lows[-period:])) / 2 - multiplier * atr_val
    if closes[-1] > basic_upper:
        return 'long', basic_lower
    elif closes[-1] < basic_lower:
        return 'short', basic_upper
    return 'neutral', 0
