"""Monitor: checks open positions for SL/TP."""
import time

class Monitor:
    def __init__(self, config, exchange, state, trader, alerts):
        self.cfg = config
        self.ex = exchange
        self.state = state
        self.trader = trader
        self.alerts = alerts

    def check(self):
        """Check all open positions."""
        positions = self.state.get('positions', {})
        for symbol, pos in list(positions.items()):
            try:
                price = self.ex.price(symbol)
            except Exception:
                continue
            entry = pos['entry']
            direction = pos['direction']
            sl = pos.get('sl', 0)
            tp = pos.get('tp', 0)
            pnl = (price - entry) / entry * 100 if direction == 'long' \
                else (entry - price) / entry * 100

            # Hard SL
            if sl and ((direction == 'long' and price <= sl) or (direction == 'short' and price >= sl)):
                self.trader.close(symbol, price, 'hard_sl')
                self.alerts.info('Monitor', f'{symbol} hard SL hit at ${price}')

            # TP
            elif tp and ((direction == 'long' and price >= tp) or (direction == 'short' and price <= tp)):
                self.trader.close(symbol, price, 'tp')
                self.alerts.info('Monitor', f'{symbol} TP hit at ${price}')

            # Max daily loss
            daily_pnl = self.state.get('daily_pnl', 0)
            if daily_pnl < -self.cfg.get('max_daily_loss_pct', 5):
                self.trader.close(symbol, price, 'daily_loss_limit')
                self.alerts.error('Monitor', f'Daily loss limit hit, closing {symbol}')
