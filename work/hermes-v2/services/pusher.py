"""Signal pusher: cross-validates and pushes signals to Feishu."""
import time

class SignalPusher:
    """Formats and pushes trading signals with cross-validation."""
    def __init__(self, config, alerts, mercu=None):
        self.cfg = config
        self.alerts = alerts
        self.mercu = mercu
        self.last_push = {}
        self.push_interval = 120  # seconds between pushes per coin

    def should_push(self, symbol):
        """Check push cooldown."""
        last = self.last_push.get(symbol, 0)
        return time.time() - last > self.push_interval

    def push(self, signal, source='v2'):
        """Push formatted signal to Feishu."""
        symbol = signal['symbol']
        if not self.should_push(symbol):
            return
        self.last_push[symbol] = time.time()

        score = signal['score']
        direction = signal['direction']
        price = signal['price']
        details = signal.get('details', {})

        # Cross-validate with MerCu if available
        cross_tag = ''
        if self.mercu:
            mc = self.mercu.get_oi_flow(symbol)
            if mc:
                oi_d = mc.get('oi_delta', 0)
                if (direction == 'long' and oi_d > 0) or (direction == 'short' and oi_d < 0):
                    cross_tag = ' [🎯MerCu共振]'
                else:
                    cross_tag = ' [⚠️MerCu分歧]'

        # Build message
        emoji = '🟢' if direction == 'long' else '🔴'
        fire = '🔥' if abs(score) >= 50 else '📊'
        body_parts = [f"{emoji} {symbol} {direction.upper()} | {abs(score)}分 {fire} ${price:.4f}{cross_tag}"]
        for k, v in list(details.items())[:5]:
            body_parts.append(f"  ↳ {v}")
        body = '\n'.join(body_parts)

        self.alerts.send(f"Signal:{symbol}", body, 'signal')
