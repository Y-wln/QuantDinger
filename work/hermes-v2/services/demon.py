"""Demon hunter: micro-cap mean reversion strategy."""
import time

class DemonHunter:
    """Mean reversion on extreme moves in small-cap coins."""
    def __init__(self, config, kline_cache, alerts):
        self.cfg = config
        self.kline = kline_cache
        self.alerts = alerts

    def hunt(self, symbol, max_mcap=50000000):
        """Check for mean reversion signal."""
        try:
            k5 = self.kline.get(symbol, '5m', 50)
            if len(k5) < 30:
                return None
            closes = [float(k['c']) for k in k5]
            current = closes[-1]
            # Extreme drop in last 10 candles
            chg_10 = (closes[-1] - closes[-10]) / closes[-10] * 100
            avg_range = sum(abs(closes[i] - closes[i-1]) / closes[i-1] * 100
                          for i in range(-10, 0)) / 10
            # Mean reversion: sharp drop + high volatility = bounce
            if chg_10 < -8 and avg_range > 1.5:
                return {'symbol': symbol, 'signal': 'mean_reversion',
                        'price': current, 'drop_pct': chg_10, 'volatility': avg_range}
        except Exception:
            pass
        return None
