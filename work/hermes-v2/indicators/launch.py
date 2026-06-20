"""Quick Launch Bonus - 3m+5m CVD sync detection for entry timing."""
def quick_launch_bonus(klines_3m, klines_5m, direction):
    """3m+5m direction sync + buy/sell ratio check.
    Returns (bonus, reasons)."""
    bonus = 0
    reasons = []

    if not klines_3m or len(klines_3m) < 3:
        return 0, []
    if not klines_5m or len(klines_5m) < 3:
        return 0, []

    try:
        # 3m direction
        c3 = float(klines_3m[-1]['c'])
        o3 = float(klines_3m[-1]['o'])
        dir_3m = 1 if c3 > o3 else (-1 if c3 < o3 else 0)

        # 5m direction
        c5 = float(klines_5m[-1]['c'])
        o5 = float(klines_5m[-1]['o'])
        dir_5m = 1 if c5 > o5 else (-1 if c5 < o5 else 0)

        # Buy/sell volume ratio on 3m
        vol3 = [float(k['v']) for k in klines_3m[-3:]]
        buy3 = sum(vol3[i] for i in range(min(3, len(klines_3m)))
                   if float(klines_3m[-(i+1)]['c']) > float(klines_3m[-(i+1)]['o']))
        total3 = sum(vol3) or 1
        buy_ratio_3m = buy3 / total3

        # 5m buy/sell ratio
        vol5 = [float(k['v']) for k in klines_5m[-3:]]
        buy5 = sum(vol5[i] for i in range(min(3, len(klines_5m)))
                   if float(klines_5m[-(i+1)]['c']) > float(klines_5m[-(i+1)]['o']))
        total5 = sum(vol5) or 1
        buy_ratio_5m = buy5 / total5

        # Sync check
        if direction == 'long' and dir_3m == 1 and dir_5m == 1:
            bonus += 5
            reasons.append('+5 3m+5m同步上涨')
        elif direction == 'short' and dir_3m == -1 and dir_5m == -1:
            bonus += 5
            reasons.append('+5 3m+5m同步下跌')

        # Buy ratio check
        if direction == 'long' and buy_ratio_3m > 0.6:
            bonus += 4
            reasons.append('+4 3m买量占比高')
        elif direction == 'short' and buy_ratio_3m < 0.4:
            bonus += 4
            reasons.append('+4 3m卖量占比高')

        if direction == 'long' and buy_ratio_5m > 0.6:
            bonus += 3
            reasons.append('+3 5m买量占比高')
        elif direction == 'short' and buy_ratio_5m < 0.4:
            bonus += 3
            reasons.append('+3 5m卖量占比高')

    except (ValueError, TypeError, IndexError):
        pass

    return bonus, reasons
