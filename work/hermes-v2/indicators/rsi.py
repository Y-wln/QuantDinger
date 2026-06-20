"""RSI indicator + divergence detection."""
def rsi(closes, period=14):
    """Calculate RSI."""
    if len(closes) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-period, 0):
        delta = closes[i] - closes[i-1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100
    return round(100 - 100 / (1 + avg_gain / avg_loss), 1)

def score_rsi(closes, period=14):
    """Score RSI. Returns (score, reason)."""
    val = rsi(closes, period)
    if val < 30:
        return 5, f'+5 RSI oversold {int(val)}'
    elif val > 70:
        return -5, f'-5 RSI overbought {int(val)}'
    elif val > 50:
        return 3, f'+3 RSI bullish {int(val)}'
    else:
        return -3, f'-3 RSI bearish {int(val)}'

def detect_rsi_divergence(klines, period=14):
    """Detect bullish/bearish RSI divergence on 4h candles."""
    if len(klines) < 30:
        return None
    closes = [float(k['c']) for k in klines]
    # Check last 2 price lows vs RSI lows
    mid = len(closes) // 2
    r1 = rsi(closes[:mid], period)
    r2 = rsi(closes[mid:], period)
    p1_min = min(closes[:mid])
    p2_min = min(closes[mid:])
    p1_max = max(closes[:mid])
    p2_max = max(closes[mid:])
    if p2_min < p1_min and r2 > r1:
        return 'bullish_divergence'
    if p2_max > p1_max and r2 < r1:
        return 'bearish_divergence'
    return None

def score_rsi_divergence(klines):
    """Score RSI divergence. Returns (score, reason)."""
    div = detect_rsi_divergence(klines)
    if div == 'bullish_divergence':
        return 12, '+12 RSI底背离'
    elif div == 'bearish_divergence':
        return -12, '-12 RSI顶背离'
    return 0, None

def rsi_exhaustion_filter(rsi_val, score):
    """RSI exhaustion: don't short when oversold, don't long when overbought."""
    if rsi_val < 25 and score < 0:
        return 8, '+8 RSI超卖(不做空)'
    elif rsi_val > 75 and score > 0:
        return -8, '-8 RSI超买(不做多)'
    elif rsi_val < 35 and score < 0:
        return 4, '+4 RSI低位(空头谨慎)'
    elif rsi_val > 65 and score > 0:
        return -4, '-4 RSI高位(多头谨慎)'
    return 0, None
