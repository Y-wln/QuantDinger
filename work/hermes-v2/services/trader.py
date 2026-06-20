"""Trader: opens and manages positions."""
import time

class Trader:
    def __init__(self, config, exchange, state, alerts, decision_log):
        self.cfg = config
        self.ex = exchange
        self.state = state
        self.alerts = alerts
        self.dlog = decision_log
        self.order_size = config.get('order_size_usdt', 50)

    def open(self, signal):
        """Open a position based on signal. Returns trade dict or None."""
        symbol = signal['symbol']
        price = signal['price']
        direction = signal['direction']
        score = signal['score']

        if self.cfg.get('mode') == 'dry-run':
            trade = {
                'symbol': symbol, 'direction': direction, 'entry': price,
                'score': score, 'ts': time.time(), 'status': 'dry_run'
            }
            self.state.add_trade(trade)
            self.dlog.trade_opened(symbol, price, self.order_size, None, None)
            self.alerts.signal(symbol, direction, score, price,
                [f'{k}:{v}' for k, v in signal.get('details', {}).items()])
            return trade

        # Live trading
        try:
            sl_price = price * (1 - self.cfg.get('hard_sl_pct', 0.08)) if direction == 'long' \
                else price * (1 + self.cfg.get('hard_sl_pct', 0.08))
            tp_price = price * (1 + self.cfg.get('tp_pct', 0.05)) if direction == 'long' \
                else price * (1 - self.cfg.get('tp_pct', 0.05))
            qty = round(self.order_size / price, 4)
            side = 'BUY' if direction == 'long' else 'SELL'

            result = self.ex.place_order(symbol, side, qty,
                stop_loss=sl_price if self.cfg.get('exchange_sl') else None,
                take_profit=tp_price if self.cfg.get('exchange_sl') else None)

            trade = {
                'symbol': symbol, 'direction': direction, 'entry': price,
                'score': score, 'ts': time.time(), 'status': 'live',
                'sl': sl_price, 'tp': tp_price, 'qty': qty,
                'order_id': result.get('orderId')
            }
            self.state.add_position(symbol, trade)
            self.state.add_trade(trade)
            self.dlog.trade_opened(symbol, price, qty, sl_price, tp_price)
            self.alerts.signal(symbol, direction, score, price,
                [f'{k}:{v}' for k, v in signal.get('details', {}).items()])
            return trade
        except Exception as e:
            self.alerts.error(f'trader.open:{symbol}', str(e))
            self.dlog.signal_rejected(symbol, f'order_error: {e}')
            return None

    def close(self, symbol, price, reason='manual'):
        """Close a position."""
        pos = self.state.get('positions', {}).get(symbol)
        if not pos:
            return None
        direction = pos['direction']
        entry = pos['entry']
        pnl_pct = (price - entry) / entry * 100 if direction == 'long' \
            else (entry - price) / entry * 100
        self.state.remove_position(symbol)
        self.dlog.trade_closed(symbol, entry, price, pnl_pct, reason)
        return {'symbol': symbol, 'entry': entry, 'exit': price, 'pnl_pct': pnl_pct, 'reason': reason}
