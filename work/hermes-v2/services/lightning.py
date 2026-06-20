"""Lightning Scanner - 10s fast CVD scan for flash signals."""
import sys, time
from indicators.cvd import calc_cvd

# Skip major coins, focus on volatile alts
SKIP = {'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'DOT', 'LINK', 'AVAX', 'LTC',
        'USDC', 'USDT', 'DAI', 'BUSD', 'TUSD', 'FDUSD', 'WBTC', 'STETH'}
COOLDOWN = 600  # 10 min per coin


class LightningScanner:
    def __init__(self, exchange, alerts, decision_log):
        self.ex = exchange
        self.alerts = alerts
        self.dlog = decision_log
        self.last_alert = {}
        self.cooldown = COOLDOWN

    def get_active_coins(self, limit=12):
        """Get most active coins by 24h change, excluding majors."""
        try:
            tickers = self.ex._call('GET', '/fapi/v1/ticker/24hr')
            if not tickers:
                return []
            filtered = []
            for d in tickers:
                sym = d.get('symbol', '')
                if not sym.endswith('USDT'):
                    continue
                name = sym.replace('USDT', '')
                if name in SKIP:
                    continue
                try:
                    chg = abs(float(d.get('priceChangePercent', 0)))
                    vol = float(d.get('quoteVolume', 0))
                    price = float(d.get('lastPrice', 0))
                except (ValueError, TypeError):
                    continue
                if vol < 100000 or price < 0.0001:
                    continue
                filtered.append((sym, chg, vol, price))
            filtered.sort(key=lambda x: x[1], reverse=True)
            return filtered[:limit]
        except Exception:
            return []

    def scan_one(self, symbol):
        """Fast CVD check on 1m candles."""
        reasons = []
        score = 0
        direction = None

        try:
            k1m = self.ex.klines(symbol, '1m', 10)
            if len(k1m) < 6:
                return None

            cv1 = calc_cvd(k1m, 4)
            # Volume check
            vols = [float(k['v']) for k in k1m[-6:]]
            avg_vol = sum(vols) / 6
            if avg_vol < 100:
                return None

            vol_ratio = vols[-1] / avg_vol if avg_vol > 0 else 1

            if cv1 > 35:
                score += 15
                reasons.append(f'1mCVD_buy_{int(cv1)}%')
                direction = 'long'
            elif cv1 < -35:
                score -= 15
                reasons.append(f'1mCVD_sell_{int(cv1)}%')
                direction = 'short'
            elif cv1 > 20:
                score += 8
                reasons.append(f'1mCVD_buy_{int(cv1)}%')
                direction = 'long'
            elif cv1 < -20:
                score -= 8
                reasons.append(f'1mCVD_sell_{int(cv1)}%')
                direction = 'short'
            else:
                return None

            # Volume confirmation
            if vol_ratio > 1.5:
                reasons.append(f'vol_x{vol_ratio:.1f}')
                if direction == 'long':
                    score += 5
                else:
                    score -= 5

            # Cooldown
            last = self.last_alert.get(symbol, 0)
            if time.time() - last < self.cooldown:
                return None

            if abs(score) < 15:
                return None

            price = float(k1m[-1]['c'])
            self.last_alert[symbol] = time.time()

            return {
                'symbol': symbol,
                'direction': direction,
                'score': score,
                'price': price,
                'reasons': reasons,
                'source': 'lightning'
            }
        except Exception:
            return None

    def scan_all(self):
        """Scan top active coins for flash signals."""
        coins = self.get_active_coins(12)
        signals = []
        for sym, chg, vol, price in coins:
            r = self.scan_one(sym)
            if r:
                signals.append(r)
        signals.sort(key=lambda x: abs(x['score']), reverse=True)
        return signals[:5]  # top 5
