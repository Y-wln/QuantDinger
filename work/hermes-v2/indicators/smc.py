"""SMC (Smart Money Concepts): Order Block + FVG detection."""
def find_swing_points(klines, lookback=5):
    """Find recent swing highs and lows."""
    if len(klines) < lookback * 2:
        return None, None
    closes = [float(k['c']) for k in klines]
    highs = [float(k['h']) for k in klines]
    lows = [float(k['l']) for k in klines]
    swing_high = max(highs[-lookback:])
    swing_low = min(lows[-lookback:])
    return swing_high, swing_low

def detect_order_block(klines, lookback=20):
    """Detect bullish/bearish order blocks.
    Bullish OB: last down candle before strong up move.
    Bearish OB: last up candle before strong down move."""
    if len(klines) < lookback + 5:
        return None
    closes = [float(k['c']) for k in klines]
    opens = [float(k['o']) for k in klines]
    highs = [float(k['h']) for k in klines]
    lows = [float(k['l']) for k in klines]

    result = {'bullish_ob': None, 'bearish_ob': None,
              'bull_strength': 0, 'bear_strength': 0}

    # Scan for bullish OB: high-to-low candle followed by 3+ up candles
    for i in range(len(klines) - 4, lookback, -1):
        if closes[i] < opens[i]:  # bearish candle
            # Check if followed by strong up move
            up_count = 0
            max_up = 0
            for j in range(i+1, min(i+6, len(klines))):
                if closes[j] > opens[j]:
                    up_count += 1
                    chg = (closes[j] - closes[i]) / closes[i] * 100
                    if chg > max_up:
                        max_up = chg
            if up_count >= 3 and max_up > 2:
                result['bullish_ob'] = highs[i]  # OB at candle high
                result['bull_strength'] = min(5, up_count)
                break

    # Scan for bearish OB: low-to-high candle followed by 3+ down candles
    for i in range(len(klines) - 4, lookback, -1):
        if closes[i] > opens[i]:  # bullish candle
            down_count = 0
            max_down = 0
            for j in range(i+1, min(i+6, len(klines))):
                if closes[j] < opens[j]:
                    down_count += 1
                    chg = (closes[i] - closes[j]) / closes[i] * 100
                    if chg > max_down:
                        max_down = chg
            if down_count >= 3 and max_down > 2:
                result['bearish_ob'] = lows[i]
                result['bear_strength'] = min(5, down_count)
                break

    return result

def detect_fvg(klines, lookback=10):
    """Detect Fair Value Gaps.
    Bullish FVG: gap between candle low and next-next candle high.
    Bearish FVG: gap between candle high and next-next candle low."""
    if len(klines) < lookback + 3:
        return None

    highs = [float(k['h']) for k in klines]
    lows = [float(k['l']) for k in klines]

    result = {'bullish_fvg': None, 'bearish_fvg': None}

    for i in range(len(klines) - 3, lookback, -1):
        # Bullish FVG: current low > 2-candles-ago high (gap up)
        if lows[i] > highs[i-2]:
            result['bullish_fvg'] = (highs[i-2], lows[i])
            break

    for i in range(len(klines) - 3, lookback, -1):
        # Bearish FVG: current high < 2-candles-ago low (gap down)
        if highs[i] < lows[i-2]:
            result['bearish_fvg'] = (lows[i-2], highs[i])
            break

    if not result['bullish_fvg'] and not result['bearish_fvg']:
        return None
    return result

def score_smc(klines_1h):
    """Score SMC signals. Returns list of (score, reason, is_leading)."""
    results = []
    if len(klines_1h) < 20:
        return results

    ob = detect_order_block(klines_1h)
    if ob:
        cur_price = float(klines_1h[-1]['c'])
        bull_ob = ob.get('bullish_ob')
        bear_ob = ob.get('bearish_ob')

        if bull_ob and abs(cur_price - bull_ob) / cur_price < 0.02 and ob.get('bull_strength', 0) >= 3:
            results.append((6, '+6 多头OB支撑', True))
        if bear_ob and abs(cur_price - bear_ob) / cur_price < 0.02 and ob.get('bear_strength', 0) >= 3:
            results.append((-6, '-6 空头OB压力', True))

    fvg = detect_fvg(klines_1h)
    if fvg:
        cur_price = float(klines_1h[-1]['c'])
        bf = fvg.get('bullish_fvg')
        brf = fvg.get('bearish_fvg')

        if bf and cur_price > bf[1] and (cur_price - bf[1]) / cur_price < 0.02:
            results.append((-4, 'FVG回补风险(下方缺口)', False))
        if brf and cur_price < brf[0] and (brf[0] - cur_price) / cur_price < 0.02:
            results.append((4, 'FVG回补机会(上方缺口)', False))

    return results
