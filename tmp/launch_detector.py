def detect_launch(klines_5m):
    if not klines_5m or len(klines_5m) < 20:
        return None, 0, []
    closes = [k['c'] for k in klines_5m]
    volumes = [k['v'] for k in klines_5m]
    highs = [k['h'] for k in klines_5m]
    lows = [k['l'] for k in klines_5m]
    range_high = max(highs[-16:-1])
    range_low = min(lows[-16:-1])
    current = closes[-1]
    range_width = (range_high - range_low) / range_low * 100
    avg_vol = sum(volumes[-11:-1]) / 10 if len(volumes) >= 11 else 1
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1
    cv5 = calc_cvd(klines_5m[-4:], 4)
    mom3 = (closes[-1] - closes[-4]) / closes[-4] * 100 if len(closes) >= 4 else 0
    up_bars = sum(1 for i in range(-4, 0) if closes[i] > closes[i-1])
    down_bars = sum(1 for i in range(-4, 0) if closes[i] < closes[i-1])
    strength = 0; reasons = []; direction = None
    if current > range_high and vol_ratio > 1.5:
        strength += 20; reasons.append('breakout_high'); direction = 'long'
    elif current < range_low and vol_ratio > 1.5:
        strength += 20; reasons.append('breakout_low'); direction = 'short'
    if cv5 > 15: strength += 15; reasons.append('5mCVD_buy'+str(int(cv5))+'%'); direction = direction or 'long'
    elif cv5 < -15: strength += 15; reasons.append('5mCVD_sell'+str(int(cv5))+'%'); direction = direction or 'short'
    elif cv5 > 8: strength += 8; reasons.append('5mCVD_buy'+str(int(cv5))+'%'); direction = direction or 'long'
    elif cv5 < -8: strength += 8; reasons.append('5mCVD_sell'+str(int(cv5))+'%'); direction = direction or 'short'
    if vol_ratio > 2.5: strength += 12; reasons.append('5m_vol_'+str(round(vol_ratio,1))+'x')
    elif vol_ratio > 1.8: strength += 6; reasons.append('5m_vol_'+str(round(vol_ratio,1))+'x')
    if mom3 > 1.5: strength += 10; reasons.append('mom_up'+str(round(mom3,1))+'%'); direction = direction or 'long'
    elif mom3 < -1.5: strength += 10; reasons.append('mom_down'+str(round(mom3,1))+'%'); direction = direction or 'short'
    if up_bars >= 3 and direction == 'long': strength += 5; reasons.append('up_bars'+str(up_bars))
    elif down_bars >= 3 and direction == 'short': strength += 5; reasons.append('down_bars'+str(down_bars))
    if range_width < 1.0 and direction: strength += 10; reasons.append('narrow_range')
    return direction, strength, reasons
