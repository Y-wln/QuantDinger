"""State persistence with snapshot and recovery."""
import json, os, time, threading

class State:
    def __init__(self, path=None):
        self.path = path or os.path.expanduser('~/hermes-v2/data/state.json')
        self.lock = threading.Lock()
        self.data = self._load()

    def _load(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            if os.path.exists(self.path):
                with open(self.path) as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return self._default()

    def _default(self):
        return {'positions': {}, 'trades': [], 'daily_pnl': 0, 'daily_trades': 0,
                'cooldowns': {}, 'last_scan': 0, 'version': 'v2'}

    def save(self):
        with self.lock:
            self.data['_saved_at'] = time.time()
            tmp = self.path + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, self.path)

    def snapshot(self):
        """Return a copy of current state for recovery."""
        with self.lock:
            return json.loads(json.dumps(self.data))

    def get(self, key, default=None):
        with self.lock:
            return self.data.get(key, default)

    def set(self, key, value):
        with self.lock:
            self.data[key] = value

    def add_trade(self, trade):
        with self.lock:
            self.data['trades'].append(trade)
            self.data['daily_trades'] += 1

    def add_position(self, symbol, pos_data):
        with self.lock:
            self.data['positions'][symbol] = pos_data

    def remove_position(self, symbol):
        with self.lock:
            self.data['positions'].pop(symbol, None)

    def position_count(self):
        with self.lock:
            return len(self.data['positions'])

    def reset_daily(self):
        with self.lock:
            self.data['daily_pnl'] = 0
            self.data['daily_trades'] = 0
