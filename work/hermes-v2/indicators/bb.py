"""Bollinger Bands indicator - squeeze detection, bandwidth, %B."""
import math

def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period

def std(values, period):
    if len(values) < period:
        return None
    avg = sma(values, period)
    variance = sum((v - avg) ** 2 for v in values[-period:]) / period
    return math.sqrt(variance)

def bollinger_bands(closes, period=20, std_mult=2.0):
    """Returns {upper, middle, lower, bandwidth, percent_b} or None."""
    if len(closes) < period:
        return None
    mid = sma(closes, period)
    stdev = std(closes, period)
    if mid is None or stdev is None:
        return None
    upper = mid + std_mult * stdev
    lower = mid - std_mult * stdev
    bandwidth = (upper - lower) / mid * 100 if mid > 0 else 20
    percent_b = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5
    return {'upper': upper, 'middle': mid, 'lower': lower,
            'bandwidth': bandwidth, 'percent_b': percent_b}

def score_bb(closes, period=20):
    """Score BB signals. Returns (score, reason, is_leading)."""
    bb = bollinger_bands(closes, period)
    if not bb:
        return 0, None, False
    bw = bb['bandwidth']
    pb = bb['percent_b']
    # Squeeze detection
    if bw < 8:
        if pb < 0.1:
            return 8, f'BB squeeze下轨 bw:{bw:.1f}%', True
        elif pb > 0.9:
            return -8, f'BB squeeze上轨 bw:{bw:.1f}%', True
        else:
            return 4, f'BB squeeze突破前兆 bw:{bw:.1f}%', True
    elif pb < 0.05:
        return 6, f'BB下轨极限 bw:{bw:.1f}%', False
    elif pb > 0.95:
        return -6, f'BB上轨极限 bw:{bw:.1f}%', False
    return 0, None, False
