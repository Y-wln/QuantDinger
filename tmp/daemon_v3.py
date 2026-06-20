"""V2 Daemon: full pipeline - orchestrator (scanner+DAG+filter) + yaobi + lightning + mercu."""
import sys, os, time, json, signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.orchestrator import Orchestrator
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

orch = Orchestrator()
mercu = MerCuBridge()
yaobi = YaobiHunter(orch.kline_cache, orch.scorer, orch.alerts, orch.dlog, mercu=mercu)
lightning = LightningScanner(orch.exchange, orch.alerts, orch.dlog)
liq_bridge = LiquidationBridge()
btc_vane = BTCVane(orch.kline_cache)

print(f"V2 Daemon | {time.strftime('%Y-%m-%d %H:%M:%S')}")
btc_trend, _, _ = btc_vane.get_btc_trend()
ver = orch.cfg.get("scorer_version", "v1")
print(f"Scorer:{ver} Main:{len(orch.cfg['scan_coins'])} Yaobi:{len(YAOBI_COINS)} Lightning:12 BTC:{btc_trend} MerCu:{'ON' if mercu.is_fresh() else 'STALE'}")
print("=" * 60)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

cycle = 0
while True:
    cycle += 1
    try:
        signal.alarm(90)
        t0 = time.time()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        # === Main strategy (scanner + DAG + filter via orchestrator) ===
        passed_signals = orch.run_once()

        # Log main signals
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

        # === MerCu signals ===
        mercu_signals = mercu.get_coin_signals()
        for ms in mercu_signals[:5]:
            ms["ts"] = ts; ms["cycle"] = cycle; ms["source"] = "mercu"
            with open(MERUCU_LOG, "a") as f:
                f.write(json.dumps(ms) + "\n")
            print(f"  [{ts}] MERCU {ms['direction']:5s} {ms['symbol']:12s} Score:{ms['score']:+4d} {ms['reasons']}")

        # === Yaobi scan ===
        try:
            yaobi_signals = yaobi.scan_all()
            for ys in yaobi_signals[:5]:
                allowed, reason = btc_vane.filter(ys["symbol"], ys["direction"])
                if not allowed:
                    continue
                ye = {"ts": ts, "cycle": cycle, "source": "yaobi",
                      "symbol": ys["symbol"], "score": ys["score"],
                      "direction": ys["direction"], "price": ys["price"],
                      "reasons": ys["reasons"]}
                with open(YAOBI_LOG, "a") as f:
                    f.write(json.dumps(ye) + "\n")
                print(f"  [{ts}] YAOBI {ys['direction']:5s} {ys['symbol']:12s} "
                      f"Score:{ys['score']:+4d} ${ys['price']:.4f}")
        except Exception as e:
            print(f"  [{ts}] YAOBI error: {e}")

        # === Lightning scan ===
        try:
            flash_signals = lightning.scan_all()
            for fs in flash_signals:
                fe = {"ts": ts, "cycle": cycle, "source": "lightning",
                      "symbol": fs["symbol"], "score": fs["score"],
                      "direction": fs["direction"], "price": fs["price"],
                      "reasons": fs["reasons"]}
                with open(LIGHTNING_LOG, "a") as f:
                    f.write(json.dumps(fe) + "\n")
                print(f"  [{ts}] FLASH {fs['direction']:5s} {fs['symbol']:12s} "
                      f"Score:{fs['score']:+4d} ${fs['price']:.4f} {fs['reasons']}")
        except Exception as e:
            print(f"  [{ts}] FLASH error: {e}")

        signal.alarm(0)
        elapsed = time.time() - t0

        if not passed_signals and not mercu_signals:
            print(f"  [{ts}] No signals (elapsed:{elapsed:.1f}s)")

        time.sleep(max(0, orch.cfg.get("scan_interval", 60) - elapsed))

    except TimeoutError:
        print(f"  [{ts}] CYCLE TIMEOUT")
    except Exception as e:
        print(f"  [{ts}] CYCLE ERROR: {e}")
        import traceback; traceback.print_exc()
        time.sleep(10)
