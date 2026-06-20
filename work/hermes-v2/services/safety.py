"""Safety: hard stop-loss and daily loss limit enforcement."""
class Safety:
    def __init__(self, config, state, alerts):
        self.cfg = config
        self.state = state
        self.alerts = alerts
        self.max_daily_loss = config.get('max_daily_loss_pct', 5)

    def check_daily_loss(self):
        """Check if daily loss limit exceeded. Returns True if trading should stop."""
        daily_pnl = self.state.get('daily_pnl', 0)
        if daily_pnl < -self.max_daily_loss:
            self.alerts.error('Safety', f'Daily loss {daily_pnl:.1f}% > {self.max_daily_loss}% limit')
            return True
        return False

    def is_safe_to_trade(self):
        """Overall safety gate."""
        if self.check_daily_loss():
            return False
        positions = self.state.get('positions', {})
        if len(positions) >= self.cfg.get('max_positions', 8):
            return False
        return True
