"""Orchestrator: main loop tying scanner, filter, trader, monitor together."""
import sys, os, time, json, traceback, threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from core.klines import KlineCache
from core.config_loader import load_config
from core.alerts import Alerts
from core.state import State
from core.pid_lock import acquire_lock, release_lock
from core.decision_log import DecisionLog
from indicators.scorer import Scorer
from services.scanner import Scanner
from services.filter import Filter
from services.trader import Trader
from services.monitor import Monitor
from services.safety import Safety
from services.dag import DAGConsensus
from services.jin10 import Jin10Bridge


class Orchestrator:
    def __init__(self, config_path=None):
        self.cfg = load_config(config_path)
        self.http = HTTPClient(retries=self.cfg['api_retries'], timeout=self.cfg['api_timeout'])
        self.exchange = ExchangeAPI(self.http)
        self.kline_cache = KlineCache(self.exchange)
        self.alerts = Alerts(webhook_url=self.cfg.get('feishu_webhook'),
                            log_dir=self.cfg.get('log_dir'))
        self.state = State(self.cfg.get('data_dir', '') + '/state.json')
        self.dlog = DecisionLog(self.cfg.get('log_dir'))
        self.scorer = Scorer()
        self.scanner = Scanner(self.cfg, self.kline_cache, self.scorer, self.alerts, self.dlog)
        self.filter = Filter(self.cfg, self.state, self.alerts, self.dlog)
        self.trader = Trader(self.cfg, self.exchange, self.state, self.alerts, self.dlog)
        self.monitor = Monitor(self.cfg, self.exchange, self.state, self.trader, self.alerts)
        self.safety = Safety(self.cfg, self.state, self.alerts)
        self.dag = DAGConsensus()
        self.jin10 = Jin10Bridge()
        self.running = False

    def run_once(self):
        """Single scan cycle."""
        try:
            # 1. Monitor existing positions
            self.monitor.check()

            # 2. Safety gate
            if not self.safety.is_safe_to_trade():
                return

            # 3. Scan all coins
            signals = self.scanner.scan_all()

            # 4. DAG consensus filter
            passed_signals, blocked_signals = self.dag.filter_signals(signals)

            # 5. Jin10 macro overlay
            if self.cfg.get('use_jin10'):
                try:
                    jin10_bonus, jin10_reasons = self.jin10.combined_bonus()
                    if jin10_bonus != 0:
                        for sig in passed_signals:
                            sig['jin10_bonus'] = jin10_bonus
                            sig['jin10_reasons'] = jin10_reasons
                except Exception:
                    pass

            # 6. Filter and trade
            for sig in passed_signals:
                passed, reason = self.filter.validate(sig)
                if passed:
                    self.trader.open(sig)
                    self.filter.set_cooldown(sig['symbol'])
                    consensus = sig.get('dag_reason', '')
                    self.alerts.info('orch',
                        f"{sig['symbol']} {sig['direction']} score={sig['score']} "
                        f"dag={consensus} OPENED")

            # 7. Save state
            self.state.set('last_scan', time.time())
            self.state.save()

        except Exception as e:
            self.alerts.error('orchestrator', traceback.format_exc())

    def run_loop(self):
        """Main loop."""
        if not acquire_lock():
            print("Another instance is running. Exiting.")
            sys.exit(1)

        self.running = True
        jin10_status = "jin10" if self.jin10.available else "no-jin10"
        self.alerts.info('orchestrator',
            f"V2 started | mode={self.cfg['mode']} | coins={len(self.cfg['scan_coins'])} | "
            f"positions={self.state.position_count()}/{self.cfg['max_positions']} | "
            f"dag+{jin10_status}")

        try:
            while self.running:
                self.run_once()
                time.sleep(self.cfg.get('scan_interval', 60))
        except KeyboardInterrupt:
            self.alerts.info('orchestrator', 'Shutting down...')
        finally:
            self.running = False
            release_lock()
            self.state.save()


def main():
    orch = Orchestrator()
    orch.run_loop()


if __name__ == '__main__':
    main()
