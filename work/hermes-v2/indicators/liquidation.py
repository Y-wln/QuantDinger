"""Liquidation magnet scoring."""
def score_liquidation(symbol, liq_data=None):
    """Score based on liquidation magnet zones. Returns (score, reason)."""
    if not liq_data or symbol not in liq_data:
        return 0, None
    data = liq_data.get(symbol, {})
    liq_long = data.get('long_liq', 0)
    liq_short = data.get('short_liq', 0)
    current = data.get('price', 0)
    if not current:
        return 0, None
    score = 0
    reasons = []
    if liq_long > 0:
        dist = (liq_long - current) / current * 100
        if -1 < dist < 0:
            score += 4
            reasons.append(f'多头清算磁吸区@${liq_long:.2f}')
        elif -3 < dist < -1:
            score += 2
            reasons.append(f'多头清算区下方@${liq_long:.2f}')
    if liq_short > 0:
        dist = (liq_short - current) / current * 100
        if 0 < dist < 1:
            score -= 4
            reasons.append(f'空头清算磁吸区@${liq_short:.2f}')
        elif 1 < dist < 3:
            score -= 2
            reasons.append(f'空头清算区上方@${liq_short:.2f}')
    if reasons:
        return score, ' | '.join(reasons)
    return 0, None

def get_liquidation_magnet(ws_data, symbol):
    """Extract liquidation zones from WebSocket data."""
    return {}
