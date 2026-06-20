"""Open Interest analysis + Funding Rate context."""
def score_oi_delta(oi_current, oi_previous, price_current, price_previous):
    """Score OI change in context of price movement.
    Returns (score, reason)."""
    if not oi_current or not oi_previous or oi_previous == 0:
        return 0, None

    oi_chg_pct = (oi_current - oi_previous) / oi_previous * 100
    price_chg_pct = (price_current - price_previous) / price_previous * 100 if price_previous else 0

    # OI up + Price up = bullish (new money entering long)
    if oi_chg_pct > 3 and price_chg_pct > 0.5:
        return 5, f'+5 OI增{oi_chg_pct:.1f}%价涨(多头加仓)'
    # OI up + Price down = bearish divergence (shorts building)
    elif oi_chg_pct > 3 and price_chg_pct < -0.5:
        return -5, f'-5 OI增{oi_chg_pct:.1f}%价跌(空头建仓)'
    # OI down + Price up = short squeeze (shorts covering)
    elif oi_chg_pct < -3 and price_chg_pct > 0.5:
        return 3, f'+3 OI降{abs(oi_chg_pct):.1f}%价涨(空头离场)'
    # OI down + Price down = bearish (longs liquidating)
    elif oi_chg_pct < -3 and price_chg_pct < -0.5:
        return -3, f'-3 OI降{abs(oi_chg_pct):.1f}%价跌(多头离场)'
    # OI surge alone
    elif oi_chg_pct > 5:
        return 4, f'+4 OI暴增{oi_chg_pct:.1f}%(变盘前兆)'
    elif oi_chg_pct < -5:
        return -4, f'-4 OI暴降{abs(oi_chg_pct):.1f}%(资金出逃)'
    return 0, None

def score_funding_rate(funding_rate):
    """Score funding rate for mean reversion signals.
    Very negative = longs get paid = shorts crowded = potential squeeze.
    Very positive = shorts get paid = longs crowded = potential dump."""
    if funding_rate is None:
        return 0, None
    fr_pct = funding_rate * 100  # convert to percentage
    # Negative funding: longs get paid, market is bearish but might reverse
    if fr_pct < -0.05:
        return 6, f'+6 极负费率({fr_pct:.3f}%)(做多信号)'
    elif fr_pct < -0.01:
        return 3, f'+3 负费率({fr_pct:.3f}%)(做多优势)'
    # Positive funding: shorts get paid, market is bullish but might reverse
    elif fr_pct > 0.1:
        return -6, f'-6 极高费率({fr_pct:.3f}%)(做空信号)'
    elif fr_pct > 0.05:
        return -3, f'-3 高正费率({fr_pct:.3f}%)(做空优势)'
    return 0, None

def oi_price_divergence(klines_4h, oi_values):
    """Detect OI-price divergence over 4h candles.
    If price makes higher high but OI makes lower high = bearish.
    If price makes lower low but OI makes higher low = bullish."""
    if len(klines_4h) < 10 or len(oi_values) < 10:
        return 0, None
    closes = [float(k['c']) for k in klines_4h[-10:]]
    ois = oi_values[-10:]
    # Price HH, OI LH = bearish divergence
    if closes[-1] > max(closes[:5]) and ois[-1] < max(ois[:5]):
        return -8, '-8 OI价背离(价格新高OI未跟)'
    # Price LL, OI HL = bullish divergence
    if closes[-1] < min(closes[:5]) and ois[-1] > min(ois[:5]):
        return 8, '+8 OI价背离(价格新低OI未跟)'
    return 0, None
