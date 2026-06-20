#!/usr/bin/env python3
"""V2 Daemon: full strategy - main + yaobi + lightning + DAG + BTC vane + launch."""
import sys, time, json, signal, traceback, os
sys.path.insert(0, '/home/ubuntu/hermes-v2')

from services.orchestrator import Orchestrator
from services.yaobi import YaobiHunter, YAOBI_COINS
from services.lightning import LightningScanner
from services.liquidation import LiquidationBridge
from services.btc_vane import BTCVane
from indicators.launch import quick_launch_bonus

LOG_FILE = '/home/ubuntu/hermes-v2/logs/v2_signals.jsonl'
YAOBI_LOG = '/home/ubuntu/hermes-v2/logs/v2_yaobi.jsonl'
LIGHTNING_LOG = '/home/ubuntu/hermes-v2/logs/v2_lightning.jsonl'

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Cycle timeout")

signal.signal(signal.SIGALRM, timeout_handler)

orch = Orchestrator()
orch.cfg['feishu_webhook'] = ''
orch.cfg['mode'] = 'dry-run'

yaobi = YaobiHunter(orch.kline_cache, orch.scorer, orch.alerts, orch.dlog)
lightning = LightningScanner(orch.exchange, orch.alerts, orch.dlog)
liq_bridge = LiquidationBridge()
btc_vane = BTCVane(orch.kline_cache)

print(f"V2 Daemon | {time.strftime('%Y-%m-%d %H:%M:%S')}")
btc_trend, _, _ = btc_vane.get_btc_trend()
print(f"Main:{len(orch.cfg['scan_coins'])} Yaobi:{len(YAOBI_COINS)} Lightning:12 BTC:{btc_trend}")
print("=" * 60)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

cycle = 0
while True:
    cycle += 1
    try:
        signal.alarm(90)
        t0 = time.time()
        ts = time.strftime('%Y-%m-%d %H:%M:%S')

        # === Main strategy ===
        signals = orch.scanner.scan_all()

        # BTC vane filter
        for sig in signals:
            allowed, reason = btc_vane.filter(sig['symbol'], sig['direction'])
            if not allowed:
                sig['btc_blocked'] = reason

        # Remove BTC-blocked signals
        signals = [s for s in signals if not s.get('btc_blocked')]

        # DAG filter
        passed_main, blocked_main = orch.dag.filter_signals(signals)

        for sig in passed_main:
            # Quick launch bonus
            try:
                sym = sig['symbol']
                k3 = orch.kline_cache.get(sym, '3m', 5, max_age=30)
                k5 = orch.kline_cache.get(sym, '5m', 50, max_age=30)
                launch_bonus, launch_reasons = quick_launch_bonus(k3, k5, sig['direction'])
                if launch_bonus:
                    sig['score'] += launch_bonus
                    for r in launch_reasons:
                        sig['details'][f'launch_{abs(launch_bonus)}'] = r
            except Exception:
                pass

            # Liquidation overlay
            liq_score, liq_reason = liq_bridge.score_liquidation(sig['symbol'], sig['price'])
            if liq_reason:
                sig['details']['liq'] = liq_reason
                sig['score'] += liq_score

            entry = {
                'ts': ts, 'cycle': cycle, 'source': 'main',
                'symbol': sig['symbol'], 'score': sig['score'],
                'direction': sig['direction'], 'price': sig['price'],
                'dag': sig.get('dag_reason', ''), 'dag_score': sig.get('dag_consensus', 0),
                'btc_trend': btc_trend,
                'details': sig['details'], 'leading': sig['leading_signals'][:5]
            }
            with open(LOG_FILE, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            liq_tag = f' Liq:{liq_score:+d}' if liq_reason else ''
            launch_tag = f' Launch:+{launch_bonus}' if 'launch_bonus' in dir() and launch_bonus else ''
            print(f"  [{ts}] MAIN {sig['direction']:5s} {sig['symbol']:12s} "
                  f"Score:{sig['score']:+4d} ${sig['price']:.4f} DAG:{sig.get('dag_consensus', 0):+2d}{launch_tag}{liq_tag}")

        # === Yaobi scan ===
        try:
            yaobi_signals = yaobi.scan_all()
            for ys in yaobi_signals[:5]:
                # BTC vane for yaobi too
                allowed, reason = btc_vane.filter(ys['symbol'], ys['direction'])
                if not allowed:
                    continue
                ye = {
                    'ts': ts, 'cycle': cycle, 'source': 'yaobi',
                    'symbol': ys['symbol'], 'score': ys['score'],
                    'direction': ys['direction'], 'price': ys['price'],
                    'reasons': ys['reasons']
                }
                with open(YAOBI_LOG, 'a') as f:
                    f.write(json.dumps(ye) + '\n')
                print(f"  [{ts}] YAOBI {ys['direction']:5s} {ys['symbol']:12s} "
                      f"Score:{ys['score']:+4d} ${ys['price']:.4f}")
        except Exception:
            pass

        # === Lightning scan ===
        try:
            flash_signals = lightning.scan_all()
            for fs in flash_signals:
                fe = {
                    'ts': ts, 'cycle': cycle, 'source': 'lightning',
                    'symbol': fs['symbol'], 'score': fs['score'],
                    'direction': fs['direction'], 'price': fs['price'],
                    'reasons': fs['reasons']
                }
                with open(LIGHTNING_LOG, 'a') as f:
                    f.write(json.dumps(fe) + '\n')
                print(f"  [{ts}] FLASH {fs['direction']:5s} {fs['symbol']:12s} "
                      f"Score:{fs['score']:+4d} ${fs['price']:.4f} {fs['reasons']}")
        except Exception:
            pass

        signal.alarm(0)
        elapsed = time.time() - t0

        if not passed_main and not yaobi_signals and not flash_signals:
            print(f"  [{ts}] No signals (elapsed:{elapsed:.1f}s)")

        orch.state.set('last_scan', time.time())
        orch.state.save()

    except TimeoutError:
        signal.alarm(0)
        print(f"  [{time.strftime('%H:%M:%S')}] TIMEOUT")
    except Exception as e:
        signal.alarm(0)
        print(f"  [{time.strftime('%H:%M:%S')}] ERROR: {e}")

    time.sleep(max(10, orch.cfg['scan_interval']))
