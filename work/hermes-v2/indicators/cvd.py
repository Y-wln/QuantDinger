"""CVD (Cumulative Volume Delta) - multi-timeframe with acceleration."""
import math

def calc_cvd(klines, n=3):
    """CVD over last n candles: sum of (close-open)*volume normalized."""
    if len(klines) < n:
        return 0
    total = 0
    for k in klines[-n:]:
        o, c, v = float(k['o']), float(k['c']), float(k['v'])
        total += (c - o) * v
    avg_vol = sum(float(k['v']) for k in klines[-n:]) / n if n > 0 else 1
    if avg_vol > 0:
        total = total / avg_vol
    return round(total, 2)

def cvd_acceleration(klines, recent_n=3, older_n=3, older_offset=24):
    """CVD slope change = smart money shift."""
    if len(klines) < older_offset + recent_n:
        return 0
    recent = calc_cvd(klines, recent_n)
    older = calc_cvd(klines[-older_offset:], older_n) if len(klines) >= older_offset else recent * 0.5
    return round(recent - older, 2)

def score_cvd_multi(k5, k15=None, k1=None):
    """Multi-timeframe CVD scoring: 5m + 15m + 1m(proxy).
    Returns list of (score, reason, is_leading)."""
    results = []

    # 5m CVD (primary)
    if k5 and len(k5) >= 10:
        cv5 = calc_cvd(k5, 3)
        if cv5 > 25:
            results.append((10, '+10 5mCVD强买', True))
        elif cv5 < -25:
            results.append((-12, '-12 5mCVD强卖', True))
        elif cv5 > 12:
            results.append((5, '+5 5mCVD买盘', False))
        elif cv5 < -12:
            results.append((-5, '-5 5mCVD卖盘', False))

    # 15m CVD
    if k15 and len(k15) >= 10:
        cv15 = calc_cvd(k15, 3)
        if cv15 > 20:
            results.append((8, '+8 15mCVD强买', True))
        elif cv15 < -20:
            results.append((-8, '-8 15mCVD强卖', True))

    # 1m CVD proxy from 5m
    if k5 and len(k5) >= 5:
        cv1 = calc_cvd(k5, 2) * 2  # approximate 1m from 2x5m candles
        if abs(cv1) > 50:
            if cv1 > 0:
                results.append((5, '+5 1mCVD买(5m推算)', False))
            else:
                results.append((-5, '-5 1mCVD卖(5m推算)', False))

    return results

def score_cvd_accel_multi(k1, k5=None):
    """Multi-timeframe CVD acceleration. Returns list of (score, reason, is_leading)."""
    results = []

    # 1h CVD acceleration
    if k1 and len(k1) >= 30:
        accel = cvd_acceleration(k1, 3, 3, 24)
        if accel > 15:
            results.append((8, '+8 CVD加速买入', True))
        elif accel < -15:
            results.append((-10, '-10 CVD加速卖出', True))
        elif accel > 8:
            results.append((4, '+4 CVD转买', False))
        elif accel < -8:
            results.append((-5, '-5 CVD转卖', False))

    # 5m CVD acceleration
    if k5 and len(k5) >= 20:
        accel5 = cvd_acceleration(k5, 3, 3, 12)
        if accel5 > 20:
            results.append((6, '+6 5mCVD加速买', True))
        elif accel5 < -20:
            results.append((-6, '-6 5mCVD加速卖', True))

    return results
