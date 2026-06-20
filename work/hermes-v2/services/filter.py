"""Filter pipeline: validates signals before trading."""
import time

class Filter:
    def __init__(self, config, state, alerts, decision_log):
        self.cfg = config
        self.state = state
        self.alerts = alerts
        self.dlog = decision_log
        self.threshold = config.get('signal_threshold', 25)
        self.cooldown_sec = 300  # 5 min between same-coin signals

    def validate(self, signal):
        """Validate a signal through the filter pipeline. Returns (passed, reason)."""
        symbol = signal['symbol']
        score = signal['score']
        direction = signal['direction']

        # 1. Score threshold
        if abs(score) < self.threshold:
            self.dlog.signal_rejected(symbol, f'score {score} < threshold {self.threshold}')
            return False, f'评分不足({abs(score)}<{self.threshold})'

        # 2. Cooldown
        cooldowns = self.state.get('cooldowns', {})
        last = cooldowns.get(symbol, 0)
        if time.time() - last < self.cooldown_sec:
            self.dlog.signal_rejected(symbol, 'cooldown')
            return False, '冷却中'

        # 3. Position limit
        if self.state.position_count() >= self.cfg.get('max_positions', 8):
            # Only allow if score is very high
            if abs(score) < self.threshold * 2:
                self.dlog.signal_rejected(symbol, 'position_limit')
                return False, '持仓已满'

        # 4. Trade coins whitelist
        trade_coins = self.cfg.get('trade_coins', self.cfg.get('scan_coins', []))
        if symbol not in trade_coins:
            self.dlog.signal_rejected(symbol, 'not in trade_coins')
            return False, '不在交易白名单'

        # 5. Already have position on this coin
        positions = self.state.get('positions', {})
        if symbol in positions:
            self.dlog.signal_rejected(symbol, 'already in position')
            return False, '已有持仓'

        self.dlog.signal_passed_filter(symbol, score, direction, signal['price'])
        return True, '通过'

    def set_cooldown(self, symbol):
        cooldowns = self.state.get('cooldowns', {})
        cooldowns[symbol] = time.time()
        self.state.set('cooldowns', cooldowns)
