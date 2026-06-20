"""Balanced RSI divergence detection - uses rolling window, not crude half-split."""
def rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100
    return round(100 - 100 / (1 + avg_gain / avg_loss), 1)


def detect_rsi_divergence(klines, period=14, lookback=20):
    """Detect divergence using rolling RSI peaks/troughs in recent lookback candles."""
    if len(klines) < lookback + period:
        return None
    closes = [float(k["c"]) for k in klines]
    recent_c = closes[-lookback:]
    recent_klines = klines[-lookback:]

    # Calculate RSI for each point in lookback
    rsi_vals = []
    for i in range(lookback):
        window = closes[max(0, len(closes) - lookback + i - period) : len(closes) - lookback + i + 1]
        if len(window) >= period + 1:
            rsi_vals.append(rsi(window, period))
        else:
            rsi_vals.append(50)

    if len(rsi_vals) < 5:
        return None

    # Find price low points (troughs) and their RSI
    price_lows = []
    rsi_at_lows = []
    for i in range(2, len(recent_c) - 2):
        if recent_c[i] <= recent_c[i - 1] and recent_c[i] <= recent_c[i - 2] and recent_c[i] <= recent_c[i + 1] and recent_c[i] <= recent_c[i + 2]:
            price_lows.append((i, recent_c[i]))
            rsi_at_lows.append((i, rsi_vals[i]))

    # Find price high points (peaks) and their RSI
    price_highs = []
    rsi_at_highs = []
    for i in range(2, len(recent_c) - 2):
        if recent_c[i] >= recent_c[i - 1] and recent_c[i] >= recent_c[i - 2] and recent_c[i] >= recent_c[i + 1] and recent_c[i] >= recent_c[i + 2]:
            price_highs.append((i, recent_c[i]))
            rsi_at_highs.append((i, rsi_vals[i]))

    # Bullish divergence: price makes lower low, RSI makes higher low
    if len(price_lows) >= 2:
        last_low_p, last_low_r = price_lows[-1][1], rsi_at_lows[-1][1]
        prev_low_p, prev_low_r = price_lows[-2][1], rsi_at_lows[-2][1]
        if last_low_p < prev_low_p and last_low_r > prev_low_r:
            return "bullish_divergence"

    # Bearish divergence: price makes higher high, RSI makes lower high
    if len(price_highs) >= 2:
        last_high_p, last_high_r = price_highs[-1][1], rsi_at_highs[-1][1]
        prev_high_p, prev_high_r = price_highs[-2][1], rsi_at_highs[-2][1]
        if last_high_p > prev_high_p and last_high_r < prev_high_r:
            return "bearish_divergence"

    return None


def score_rsi(closes, period=14):
    val = rsi(closes, period)
    if val < 30:
        return 5, f"+5 RSI oversold {int(val)}"
    elif val > 70:
        return -5, f"-5 RSI overbought {int(val)}"
    elif val > 50:
        return 3, f"+3 RSI bullish {int(val)}"
    else:
        return -3, f"-3 RSI bearish {int(val)}"


def score_rsi_divergence(klines):
    div = detect_rsi_divergence(klines)
    if div == "bullish_divergence":
        return 12, "+12 RSI???"
    elif div == "bearish_divergence":
        return -12, "-12 RSI???"
    return 0, None


def rsi_exhaustion_filter(rsi_val, score):
    if rsi_val < 25 and score < 0:
        return 8, "+8 RSI??(???)"
    elif rsi_val > 75 and score > 0:
        return -8, "-8 RSI??(???)"
    elif rsi_val < 35 and score < 0:
        return 4, "+4 RSI??(????)"
    elif rsi_val > 65 and score > 0:
        return -4, "-4 RSI??(????)"
    return 0, None
