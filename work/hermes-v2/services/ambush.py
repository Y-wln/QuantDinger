"""Ambush scanner: predictive signals for early entry."""
import time, json, os

class AmbushScanner:
    """Looks for early warning patterns before main signal fires."""
    def __init__(self, config, kline_cache, alerts):
        self.cfg = config
        self.kline = kline_cache
        self.alerts = alerts
        self.coins = config.get('scan_coins', [])

    def scan(self, symbol=None):
        """Scan for ambush patterns. Returns list of potential signals."""
        targets = [symbol] if symbol else self.coins
        results = []
        for sym in targets:
            try:
                k1 = self.kline.get(sym, '1h', 50)
                k15 = self.kline.get(sym, '15m', 30)
                if len(k1) < 20:
                    continue
                closes = [float(k['c']) for k in k1]
                current = closes[-1]
                # Pattern: tight consolidation then micro-breakout
                recent_range = (max(closes[-5:]) - min(closes[-5:])) / current * 100
                prev_range = (max(closes[-20:-5]) - min(closes[-20:-5])) / current * 100
                if recent_range < 1.5 and prev_range > 3:
                    results.append({
                        'symbol': sym, 'pattern': 'coil_compression',
                        'price': current, 'confidence': 'medium'
                    })
                # Pattern: price at key level with reducing volume
                vols = [float(k['v']) for k in k1]
                vol_ratio = sum(vols[-3:]) / max(1, sum(vols[-8:-3])) * 5/3
                if vol_ratio < 0.5 and abs((current - closes[-20]) / closes[-20]) < 0.02:
                    results.append({
                        'symbol': sym, 'pattern': 'volume_dry_up_at_support',
                        'price': current, 'confidence': 'medium'
                    })
            except Exception:
                continue
        return results
