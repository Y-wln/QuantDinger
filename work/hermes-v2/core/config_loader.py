"""Load and validate config.yaml."""
import os, yaml

_default_config = """
mode: dry-run
max_positions: 8
signal_threshold: 25
scan_interval: 60
max_daily_loss_pct: 5
use_mercu: true
use_jin10: true
use_liq_ws: true
"""

def load_config(path=None):
    if not path:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')
    if not os.path.exists(path):
        cfg = yaml.safe_load(_default_config)
    else:
        with open(path, 'r') as f:
            cfg = yaml.safe_load(f)
    cfg.setdefault('mode', 'dry-run')
    cfg.setdefault('max_positions', 8)
    cfg.setdefault('signal_threshold', 25)
    cfg.setdefault('scan_interval', 60)
    cfg.setdefault('scan_coins', ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])
    cfg.setdefault('trade_coins', cfg['scan_coins'])
    cfg.setdefault('max_daily_loss_pct', 5)
    cfg.setdefault('hard_sl_pct', 0.08)
    cfg.setdefault('tp_pct', 0.05)
    cfg.setdefault('api_retries', 3)
    cfg.setdefault('api_timeout', 10)
    cfg.setdefault('use_mercu', True)
    cfg.setdefault('use_jin10', True)
    cfg.setdefault('use_liq_ws', True)
    cfg.setdefault('data_dir', os.path.expanduser('~/hermes-v2/data'))
    cfg.setdefault('log_dir', os.path.expanduser('~/hermes-v2/logs'))
    return cfg
