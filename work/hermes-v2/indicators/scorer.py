"""Combined scorer: aggregates all indicator scores into final trading signal."""
from indicators import bb, cvd, rsi, macd, structure, volume, candles, orderbook, smc, hvn

class Scorer:
    def __init__(self):
        self.threshold = 25

    def analyze(self, symbol, k4, k1, k5, k15, funding_rate=0, fng=50, liq_data=None):
        c4 = [float(k['c']) for k in k4]
        c1 = [float(k['c']) for k in k1]
        score = 0
        details = {}
        leading = []

        rsi1h_val = rsi.rsi(c1) if len(c1) >= 14 else 50
        rsi4_val = rsi.rsi(c4) if len(c4) >= 14 else 50

        # PART 1: LEADING
        s, r, is_lead = bb.score_bb(c1)
        if r: score += s; details['bb1h'] = r
        if is_lead: leading.append(r)

        for s, r, is_lead in cvd.score_cvd_multi(k5, k15, k1):
            score += s; details[f'cvd_{abs(s)}'] = r
            if is_lead: leading.append(r)

        for s, r, is_lead in cvd.score_cvd_accel_multi(k1, k5):
            score += s; details[f'cvd_accel_{abs(s)}'] = r
            if is_lead: leading.append(r)

        for s, r, is_lead in orderbook.score_orderbook_tape(k1):
            score += s; details[f'ob_{abs(s)}'] = r
            if is_lead: leading.append(r)

        for s, r, is_lead in smc.score_smc(k1):
            score += s; details[f'smc_{abs(s)}'] = r
            if is_lead: leading.append(r)

        # PART 2: TECHNICAL
        s, r = rsi.score_rsi(c4)
        if r: score += s; details['rsi'] = r

        s, r = rsi.score_rsi_divergence(k4)
        if r: score += s; details['rsi_div'] = r; leading.append(r)

        s, r = rsi.rsi_exhaustion_filter(rsi1h_val, score)
        if r: score += s; details['rsi_filter'] = r
        if abs(s) >= 8: leading.append(r)

        s, r = macd.score_macd(c4)
        if r: score += s; details['macd'] = r

        # PART 3: STRUCTURE
        results, s4, s1 = structure.score_structure(k4, k1)
        for s_item, r_item in results:
            score += s_item; details[f'struct_{abs(s_item)}'] = r_item

        st4, _ = macd.supertrend(k4)
        if st4 == 'long': score += 4; details['st4'] = '+4 ST long'
        else: score -= 4; details['st4'] = '-4 ST short'

        # PART 4: MOMENTUM + VOLUME + CANDLES
        from indicators.momentum import momentum_score, score_momentum
        s, r, is_lead = score_momentum(k4)
        if r: score += s; details['momentum'] = r
        if is_lead: leading.append(r)

        s, r, is_lead = volume.score_volume_surge(k4)
        if r: score += s; details['vol_surge'] = r
        if is_lead: leading.append(r)

        s, r = volume.score_atr_volatility(k1)
        if r: score += s; details['atr'] = r

        # Candle patterns (all from candles.py)
        for s_item, r_item in candles.score_rejection(k1):
            score += s_item; details['rejection'] = r_item
        for s_item, r_item in candles.score_rejection(k4):
            score += s_item; details['rej_4h'] = r_item
        for s_item, r_item in candles.score_engulfing(k1):
            score += s_item; details['engulfing'] = r_item
            if abs(s_item) >= 8: leading.append(r_item)
        for s_item, r_item in candles.score_engulfing(k4):
            score += s_item; details['engulfing_4h'] = r_item

        # HVN/LVN
        for s_item, r_item, is_lead in hvn.score_hvn(k1):
            score += s_item; details['hvn'] = r_item

        # ADX
        s, r = macd.score_adx(k1, score)
        if s: score += s; details['adx'] = r

        # PART 5: SENTIMENT
        if fng <= 20:
            if s4 == 'down': score -= 8; details['fng'] = '-8 极度恐慌+趋势向下'; leading.append('恐慌踩踏做空')
            elif s4 == 'up': score += 5; details['fng'] = '+5 极度恐慌+趋势上涨'
        elif fng >= 80:
            if s4 == 'up': score -= 8; details['fng'] = '-8 极度贪婪+趋势向上'
            elif s4 == 'down': score += 5; details['fng'] = '+5 极度贪婪+趋势下跌'

        if funding_rate < -0.005: score += 3; details['fr'] = '+3 负费率'
        elif funding_rate > 0.01: score -= 3; details['fr'] = '-3 高正费率'

        # PART 6: REGIME
        s, r = structure.regime_amplifier(s4, s1, score)
        if r: score += s; details['regime'] = r

        # FINAL
        if score >= self.threshold: direction = 'long'; signal = 'buy'
        elif score <= -self.threshold: direction = 'short'; signal = 'sell'
        else: direction = 'neutral'; signal = 'wait'

        return {
            'score': score, 'signal': signal, 'direction': direction,
            'price': float(k1[-1]['c']) if k1 else 0,
            'details': details, 'leading_signals': leading, 'symbol': symbol
        }
