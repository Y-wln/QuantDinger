"""Decision log: records every signal's full lifecycle."""
import json, os, time

class DecisionLog:
    def __init__(self, log_dir=None):
        self.log_dir = log_dir or os.path.expanduser('~/hermes-v2/logs')
        self.dir = os.path.join(self.log_dir, 'decisions')
        os.makedirs(self.dir, exist_ok=True)

    def _file(self, symbol):
        date = time.strftime('%Y%m%d')
        return os.path.join(self.dir, f"{symbol}_{date}.jsonl")

    def log(self, symbol, event, data):
        entry = {
            'ts': time.time(),
            'iso': time.strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'event': event,
            'data': data
        }
        with open(self._file(symbol), 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def signal_detected(self, symbol, score, direction, price, indicators):
        self.log(symbol, 'signal_detected', {
            'score': score, 'direction': direction, 'price': price,
            'indicators': indicators
        })

    def signal_passed_filter(self, symbol, score, direction, price):
        self.log(symbol, 'signal_passed_filter', {
            'score': score, 'direction': direction, 'price': price
        })

    def signal_rejected(self, symbol, reason):
        self.log(symbol, 'signal_rejected', {'reason': reason})

    def trade_opened(self, symbol, price, quantity, sl, tp):
        self.log(symbol, 'trade_opened', {
            'price': price, 'quantity': quantity, 'sl': sl, 'tp': tp
        })

    def trade_closed(self, symbol, entry_price, exit_price, pnl, reason):
        self.log(symbol, 'trade_closed', {
            'entry_price': entry_price, 'exit_price': exit_price,
            'pnl': pnl, 'reason': reason
        })

    def indicator_snapshot(self, symbol, indicators):
        self.log(symbol, 'indicator_snapshot', indicators)
