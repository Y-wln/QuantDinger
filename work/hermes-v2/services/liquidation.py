"""Liquidation Heatmap Bridge - reads V1 liq_ws data for V2."""
import sys, os, json, time


class LiquidationBridge:
    """Bridge to V1's liq_ws liquidation data."""
    def __init__(self):
        self.cache_path = '/home/ubuntu/scripts/agents/liquidation_live.json'
        self.available = os.path.exists(self.cache_path)

    def get_data(self):
        """Read latest liquidation data. Returns dict or empty."""
        if not self.available:
            return {}
        try:
            mtime = os.path.getmtime(self.cache_path)
            if time.time() - mtime > 300:  # stale after 5 min
                return {}
            with open(self.cache_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def get_for_symbol(self, symbol):
        """Get liquidation data for a specific symbol."""
        data = self.get_data()
        if not data:
            return {}
        name = symbol.replace('USDT', '')
        return data.get(name, data.get(symbol, {}))

    def score_liquidation(self, symbol, price):
        """Score liquidation magnet proximity.
        Returns (score, reason) or (0, None)."""
        data = self.get_for_symbol(symbol)
        if not data or not price:
            return 0, None

        long_liq = data.get('long_liq', 0)
        short_liq = data.get('short_liq', 0)
        score = 0
        reasons = []

        if long_liq and long_liq > 0:
            dist = (price - long_liq) / price * 100
            if -1 < dist < 0:
                score -= 4
                reasons.append(f'多头清算区@${long_liq:.2f}')
            elif -3 < dist < -1:
                score -= 2
                reasons.append(f'多头清算磁吸@${long_liq:.2f}')

        if short_liq and short_liq > 0:
            dist = (price - short_liq) / price * 100
            if 0 < dist < 1:
                score += 4
                reasons.append(f'空头清算区@${short_liq:.2f}')
            elif 1 < dist < 3:
                score += 2
                reasons.append(f'空头清算磁吸@${short_liq:.2f}')

        if reasons:
            return score, ' | '.join(reasons)
        return 0, None
