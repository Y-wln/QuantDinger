"""BTC风向标 - macro filter: BTC trend gates altcoin direction."""
from indicators.structure import detect_structure

class BTCVane:
    """Checks BTC 4h trend. In BTC downtrend, blocks altcoin longs.
    In BTC uptrend, blocks altcoin shorts. Neutral = allow all."""

    # Tier 1: high-cap alts that follow BTC closely
    BTC_TIER1 = {'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT',
                 'LINKUSDT', 'AVAXUSDT', 'DOTUSDT', 'LTCUSDT'}

    def __init__(self, kline_cache):
        self.kline = kline_cache
        self._btc_klines = None
        self._last_fetch = 0

    def get_btc_trend(self):
        """Returns (trend, allow_long, allow_short)."""
        import time
        now = time.time()
        if self._btc_klines and now - self._last_fetch < 300:
            k4 = self._btc_klines
        else:
            k4 = self.kline.get('BTCUSDT', '4h', 100)
            self._btc_klines = k4
            self._last_fetch = now

        if len(k4) < 50:
            return 'unknown', True, True

        struct, _ = detect_structure(k4)
        trend = 'down' if struct == 'down' else ('up' if struct == 'up' else 'neutral')
        return trend, trend != 'down', trend != 'up'

    def filter(self, symbol, direction):
        """Check if a trade direction is allowed given BTC trend.
        Returns (allowed, reason)."""
        trend, allow_long, allow_short = self.get_btc_trend()

        if trend == 'unknown':
            return True, ''

        if direction == 'long' and not allow_long:
            return False, f'BTC{trend}趋势-禁止做多山寨'

        if direction == 'short' and not allow_short:
            return False, f'BTC{trend}趋势-禁止做空山寨'

        # Tier 1 coins are more coupled to BTC
        if symbol in self.BTC_TIER1:
            if direction == 'long' and trend == 'down':
                return False, f'BTC{trend}-Tier1禁止做多'
            if direction == 'short' and trend == 'up':
                return False, f'BTC{trend}-Tier1禁止做空'

        return True, ''
