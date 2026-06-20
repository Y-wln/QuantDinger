"""HVN/LVN Volume Profile - high/low volume node detection."""
def volume_profile_zones(klines, bins=10):
    """Find High Volume Nodes (support/resistance) and Low Volume Nodes.
    HVN = price level where lots of volume traded (likely support/resistance).
    LVN = price level with little volume (likely to break through quickly)."""
    if len(klines) < 20:
        return None

    highs = [float(k['h']) for k in klines[-30:]]
    lows = [float(k['l']) for k in klines[-30:]]
    volumes = [float(k['v']) for k in klines[-30:]]
    closes = [float(k['c']) for k in klines]

    price_min = min(lows)
    price_max = max(highs)
    if price_max <= price_min:
        return None

    bin_size = (price_max - price_min) / bins
    histogram = [0.0] * bins
    for i, k in enumerate(klines[-30:]):
        mid = (float(k['h']) + float(k['l'])) / 2
        idx = min(bins - 1, max(0, int((mid - price_min) / bin_size)))
        histogram[idx] += volumes[i]

    avg_vol = sum(histogram) / bins if bins > 0 else 1
    hvns = []
    lvns = []
    for i, v in enumerate(histogram):
        zone_price = round(price_min + bin_size * (i + 0.5), 4)
        if v > avg_vol * 1.5:
            hvns.append((zone_price, round(v, 0)))
        elif v < avg_vol * 0.5:
            lvns.append((zone_price, round(v, 0)))

    current = closes[-1]
    in_hvn = any(abs(current - p) / current < 0.01 for p, _ in hvns)
    nearest_hvn = min(hvns, key=lambda x: abs(current - x[0]))[0] if hvns else None
    nearest_lvn = min(lvns, key=lambda x: abs(current - x[0]))[0] if lvns else None

    return {
        'hvns': hvns[:5],
        'lvns': lvns[:5],
        'current_in_hvn': in_hvn,
        'nearest_hvn': nearest_hvn,
        'nearest_lvn': nearest_lvn,
        'current': round(current, 4)
    }

def score_hvn(klines):
    """Score HVN/LVN zones. Returns list of (score, reason, is_leading)."""
    results = []
    vp = volume_profile_zones(klines)
    if not vp:
        return results

    cur = vp['current']
    if vp.get('current_in_hvn'):
        results.append((4, '+4 HVN支撑区', False))
    nhvn = vp.get('nearest_hvn')
    if nhvn and abs(nhvn - cur) / cur < 0.02:
        results.append((0, f'HVN@{int(nhvn)}', False))
    nlvn = vp.get('nearest_lvn')
    if nlvn and abs(nlvn - cur) / cur < 0.02:
        results.append((0, f'LVN@{int(nlvn)}', False))

    return results
