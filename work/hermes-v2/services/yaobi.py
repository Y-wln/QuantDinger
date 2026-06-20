"""Yaobi Hunter V2 - Microcap scanner with mean-reversion + CVD + MerCu bonus."""
import sys, os, time, json
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

# Fixed scan list - micro/small cap coins with high volatility
YAOBI_COINS = [
    "IOUSDT", "ENAUSDT", "TAOUSDT", "ONDOUSDT", "ALLOUSDT", "TRUMPUSDT",
    "STGUSDT", "AIOUSDT", "PLAYUSDT", "SYNUSDT", "PORTALUSDT", "OPENUSDT",
    "COAIUSDT", "MEGAUSDT", "CHIPUSDT", "ESPORTSUSDT", "SENTUSDT",
    "JASMYUSDT", "ALGOUSDT", "FETUSDT", "WLDUSDT", "HYPEUSDT",
    "INJUSDT", "APTUSDT", "DASHUSDT", "ZECUSDT", "AAVEUSDT", "JCTUSDT"
]


class YaobiHunter:
    def __init__(self, kline_cache, scorer, alerts, decision_log, mercu=None):
        self.kline = kline_cache
        self.scorer = scorer
        self.alerts = alerts
        self.dlog = decision_log
        self.mercu = mercu
        self.cooldowns = {}

    def calc_vwap(self, klines_5m, n=24):
        """VWAP from last n 5m candles (~2 hours)."""
        if not klines_5m or len(klines_5m) < n:
            return 0
        total_pv = 0
        total_v = 0
        for k in klines_5m[-n:]:
            h, l, c, v = float(k['h']), float(k['l']), float(k['c']), float(k['v'])
            typical = (h + l + c) / 3
            total_pv += typical * v
            total_v += v
        return total_pv / total_v if total_v > 0 else 0

    def get_mercu_bonus(self, symbol_clean, direction):
        """Bonus from MerCu data."""
        bonus = 0
        labels = []
        if not self.mercu:
            return 0, []

        sym = symbol_clean.upper()

        # Anomaly states
        anom = self.mercu.read_latest('anomaly')
        if anom:
            for s in anom.get('state_anomalies', anom.get('anomalies', [])):
                if str(s.get('symbol', s.get('sym', ''))).upper() == sym:
                    scenario = s.get('scenario', '')
                    if direction == 'short' and scenario in ('DISTRIB', 'BEAR'):
                        bonus += 15
                        labels.append('MER:' + scenario)
                    elif direction == 'long' and scenario in ('ACCUM', 'BULL'):
                        bonus += 15
                        labels.append('MER:' + scenario)

        # Rank
        rank = self.mercu.read_latest('rank')
        if rank:
            for item in rank.get('top', [])[:5]:
                if str(item.get('sym', '')).replace('$', '').upper() == sym:
                    bonus += 5
                    labels.append(f'Rank#{item.get("rank", 0)}')
                    break

        # Surge
        surge = self.mercu.read_latest('surge')
        if surge:
            for item in surge.get('items', []):
                if str(item.get('sym', '')).upper() == sym:
                    accel = float(item.get('accel', 0))
                    if accel >= 1.5:
                        bonus += 8
                        labels.append(f'Surge:x{accel:.1f}')
                    break

        return bonus, labels

    def scan_one(self, symbol):
        """Scan single microcap coin. Returns signal dict or None."""
        try:
            # Cooldown
            last = self.cooldowns.get(symbol, 0)
            if time.time() - last < 300:
                return None

            k5 = self.kline.get(symbol, '5m', 50)
            k1 = self.kline.get(symbol, '1h', 50)
            if not k5 or len(k5) < 30:
                return None

            closes = [float(k['c']) for k in k5]
            current = closes[-1]
            score = 0
            reasons = []
            direction = None

            # 1. CVD on 5m
            from indicators.cvd import calc_cvd
            cv5 = calc_cvd(k5, 3)
            if cv5 > 30:
                score += 20
                reasons.append(f'5mCVD_buy({int(cv5)}%)')
                direction = 'long'
            elif cv5 < -30:
                score -= 20
                reasons.append(f'5mCVD_sell({int(cv5)}%)')
                direction = 'short'
            elif cv5 > 15:
                score += 10
                reasons.append(f'5mCVD_buy({int(cv5)}%)')
                direction = 'long'
            elif cv5 < -15:
                score -= 10
                reasons.append(f'5mCVD_sell({int(cv5)}%)')
                direction = 'short'
            else:
                return None  # No clear direction

            # 2. VWAP mean reversion
            if k1 and len(k1) >= 20:
                vwap = self.calc_vwap(k5)
                if vwap > 0:
                    dist = (current - vwap) / vwap * 100
                    if direction == 'long' and dist < -3:
                        score += 10
                        reasons.append(f'VWAP下方{dist:.1f}%(超卖)')
                    elif direction == 'short' and dist > 3:
                        score -= 10
                        reasons.append(f'VWAP上方{dist:.1f}%(超买)')

            # 3. Volume surge
            if len(k5) >= 12:
                vols = [float(k['v']) for k in k5]
                avg_vol = sum(vols[-12:]) / 12
                recent_vol = sum(vols[-3:]) / 3
                ratio = recent_vol / avg_vol if avg_vol > 0 else 1
                if ratio > 2.0:
                    if direction == 'long':
                        score += 8
                        reasons.append(f'vol_x{ratio:.1f}')
                    else:
                        score -= 8
                        reasons.append(f'vol_x{ratio:.1f}')

            # 4. Candles in direction
            green_count = 0
            red_count = 0
            for k in k5[-3:]:
                if float(k['c']) > float(k['o']):
                    green_count += 1
                else:
                    red_count += 1
            if direction == 'long' and green_count >= 2:
                score += 5
                reasons.append(f'{green_count}green')
            elif direction == 'short' and red_count >= 2:
                score -= 5
                reasons.append(f'{red_count}red')

            # 5. MerCu bonus
            sym_clean = symbol.replace('USDT', '')
            mc_bonus, mc_labels = self.get_mercu_bonus(sym_clean, direction)
            score += mc_bonus
            reasons.extend(mc_labels)

            # Threshold
            if abs(score) < 20:
                return None

            self.cooldowns[symbol] = time.time()

            return {
                'symbol': symbol,
                'score': score,
                'direction': direction,
                'price': current,
                'reasons': reasons,
                'source': 'yaobi'
            }

        except Exception:
            return None

    def scan_all(self):
        """Scan all yaobi coins, return list of signals sorted by abs(score)."""
        signals = []
        for sym in YAOBI_COINS:
            r = self.scan_one(sym)
            if r:
                signals.append(r)
        signals.sort(key=lambda x: abs(x['score']), reverse=True)
        return signals
