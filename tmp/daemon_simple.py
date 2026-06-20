"""V2 Daemon: simplified - uses scanner directly (bypasses orchestrator)."""
import sys, os, time, json, signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.http_client import HTTPClient
from core.exchange import ExchangeAPI
from core.klines import KlineCache
from core.config_loader import load_config
from core.alerts import Alerts
from core.state import State
from core.decision_log import DecisionLog
from services.scanner import Scanner
from services.dag import DAGConsensus
from services.yaobi import YaobiHunter, YAOBI_COINS
from services.lightning import LightningScanner
from services.liquidation import LiquidationBridge
from services.btc_vane import BTCVane
from services.mercu import MerCuBridge

LOG_FILE = "/home/ubuntu/hermes-v2/logs/v2_signals.jsonl"
YAOBI_LOG = "/home/ubuntu/hermes-v2/logs/v2_yaobi.jsonl"
LIGHTNING_LOG = "/home/ubuntu/hermes-v2/logs/v2_lightning.jsonl"
MERUCU_LOG = "/home/ubuntu/hermes-v2/logs/v2_mercu.jsonl"


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("Cycle timeout")


signal.signal(signal.SIGALRM, timeout_handler)

print(f"V2 Daemon | {time.strftime('%Y-%m-%d %H:%M:%S')}")

# Init
cfg = load_config()
http = HTTPClient(retries=cfg["api_retries"], timeout=cfg["api_timeout"])
ex = ExchangeAPI(http)
kc = KlineCache(ex)
alerts = Alerts(webhook_url=cfg.get("feishu_webhook"), log_dir=cfg.get("log_dir"))
state = State(cfg.get("data_dir", "") + "/state.json")
dlog = DecisionLog(cfg.get("log_dir"))

# Scorer
ver = cfg.get("scorer_version", "v1")
if ver == "v2":
    from indicators.scorer_v2 import ScorerV2
    scorer = ScorerV2()
else:
    from indicators.scorer import Scorer
    scorer = Scorer()

scanner = Scanner(cfg, kc, scorer, alerts, dlog)
dag = DAGConsensus()
mercu = MerCuBridge()
yaobi = YaobiHunter(kc, scorer, alerts, dlog, mercu=mercu)
lightning = LightningScanner(ex, alerts, dlog)
btc_vane = BTCVane(kc)

# Pre-warm cache
print("Pre-warming kline cache...")
all_coins = list(set(cfg["scan_coins"] + list(YAOBI_COINS)))
for i, sym in enumerate(all_coins):
    print(f"  [{i+1}/{len(all_coins)}] {sym}...", end=" ", flush=True)
    t0 = time.time()
    try:
        kc.get(sym, "4h", 300)
        kc.get(sym, "1h", 300)
        kc.get(sym, "5m", 50)
        kc.get(sym, "15m", 30)
        print(f"OK ({time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"FAIL ({e})")
    time.sleep(0.3)

print("Cache warm. Starting loop...")
btc_trend, _, _ = btc_vane.get_btc_trend()
print(f"Scorer:{ver} Coins:{len(cfg['scan_coins'])} Yaobi:{len(YAOBI_COINS)} BTC:{btc_trend} MerCu:{'ON' if mercu.is_fresh() else 'STALE'}")
print("=" * 60)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

cycle = 0
while True:
    cycle += 1
    try:
        signal.alarm(90)
        t0 = time.time()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        # === Main scan ===
        raw_signals = scanner.scan_all()
        passed_signals, blocked = dag.filter_signals(raw_signals)

        for sig in passed_signals:
            entry = {
                "ts": ts, "cycle": cycle, "source": "main",
                "symbol": sig["symbol"], "score": sig["score"],
                "direction": sig["direction"], "price": sig["price"],
                "filter_passed": True,
                "details": sig.get("details", {}),
                "leading": sig.get("leading_signals", []),
                "dag": sig.get("dag_consensus", 0),
                "dag_score": sig.get("dag_consensus", 0),
                "btc_trend": btc_trend,
            }
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
            print(f"  [{ts}] MAIN {sig['direction']:5s} {sig['symbol']:12s} "
                  f"Score:{sig['score']:+4d} ${sig['price']:.4f} DAG:{sig.get('dag_consensus', 0):+2d}")

        if blocked:
            print(f"  [{ts}] DAG blocked {len(blocked)} signals")

        # === MerCu signals ===
        mercu_signals = mercu.get_coin_signals()
        for ms in mercu_signals[:5]:
            ms["ts"] = ts; ms["cycle"] = cycle; ms["source"] = "mercu"
            with open(MERUCU_LOG, "a") as f:
                f.write(json.dumps(ms) + "\n")
            print(f"  [{ts}] MERCU {ms['direction']:5s} {ms['symbol']:12s} Score:{ms['score']:+4d} {ms['reasons']}")

        # === Yaobi ===
        try:
            yaobi_signals = yaobi.scan_all()
            for ys in yaobi_signals[:5]:
                ye = {"ts": ts, "cycle": cycle, "source": "yaobi",
                      "symbol": ys["symbol"], "score": ys["score"],
                      "direction": ys["direction"], "price": ys["price"],
                      "reasons": ys.get("reasons", [])}
                with open(YAOBI_LOG, "a") as f:
                    f.write(json.dumps(ye) + "\n")
                print(f"  [{ts}] YAOBI {ys['direction']:5s} {ys['symbol']:12s} Score:{ys['score']:+4d}")
        except Exception as e:
            pass  # yaobi may have no signals

        # === Lightning ===
        try:
            flash_signals = lightning.scan_all()
            for fs in flash_signals:
                fe = {"ts": ts, "cycle": cycle, "source": "lightning",
                      "symbol": fs["symbol"], "score": fs["score"],
                      "direction": fs["direction"], "price": fs["price"],
                      "reasons": fs.get("reasons", [])}
                with open(LIGHTNING_LOG, "a") as f:
                    f.write(json.dumps(fe) + "\n")
                print(f"  [{ts}] FLASH {fs['direction']:5s} {fs['symbol']:12s} Score:{fs['score']:+4d}")
        except Exception as e:
            pass

        signal.alarm(0)
        elapsed = time.time() - t0
        if not passed_signals and not mercu_signals:
            print(f"  [{ts}] No signals (elapsed:{elapsed:.1f}s)")

        time.sleep(max(0, cfg.get("scan_interval", 60) - elapsed))

    except TimeoutError:
        print(f"  [{ts}] CYCLE TIMEOUT ({time.time()-t0:.0f}s)")
    except Exception as e:
        print(f"  [{ts}] CYCLE ERROR: {e}")
        import traceback; traceback.print_exc()
        time.sleep(10)
