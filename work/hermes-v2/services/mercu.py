"""MerCu data integration: reads real-time data files from mercu poller."""
import json, os, time, glob

class MerCuBridge:
    """Reads MerCu data from files polled by mercu_headless.py."""
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or os.path.expanduser('~/hermes-v2/data/mercu')
        os.makedirs(self.data_dir, exist_ok=True)

    def read_latest(self, data_type='anomaly'):
        """Read latest MerCu data file of given type."""
        pattern = os.path.join(self.data_dir, f'{data_type}_*.json')
        files = sorted(glob.glob(pattern), reverse=True)
        if not files:
            return {}
        try:
            with open(files[0]) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def get_oi_flow(self, symbol):
        """Get OI flow data for a symbol."""
        data = self.read_latest('dashboard')
        if not data:
            return {}
        for coin in data.get('coins', []):
            if coin.get('symbol') == symbol.replace('USDT', ''):
                return {
                    'oi_delta': coin.get('oi_delta', 0),
                    'perp_flow': coin.get('perp_flow', 0),
                    'spot_flow': coin.get('spot_flow', 0),
                    'price': coin.get('price', 0),
                    'plaza_signal': coin.get('plaza', 'neutral'),
                }
        return {}

    def get_anomalies(self, limit=20):
        """Get recent anomalies."""
        return self.read_latest('anomaly').get('anomalies', [])[:limit]

    def get_momentum(self):
        """Get momentum rankings."""
        return self.read_latest('momentum')

    def get_surge(self):
        """Get volume surge data."""
        return self.read_latest('surge')

    def is_fresh(self, max_age=60):
        """Check if data is fresh (< max_age seconds old)."""
        pattern = os.path.join(self.data_dir, 'anomaly_*.json')
        files = sorted(glob.glob(pattern), reverse=True)
        if not files:
            return False
        mtime = os.path.getmtime(files[0])
        return (time.time() - mtime) < max_age
