import sys, os, time, json, signal
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
orch.cfg["feishu_webhook"] = ""
orch.cfg["mode"] = "dry-run"

mercu = MerCuBridge()
yaobi = YaobiHunter(orch.kline_cache, orch.scorer, orch.alerts, orch.dlog, mercu=mercu)
lightning = LightningScanner(orch.exchange, orch.alerts, orch.dlog)
liq_bridge = LiquidationBridge()
btc_vane = BTCVane(orch.kline_cache)

print(f"V2 Daemon | {time.strftime('%Y-%m-%d %H:%M:%S')}")
btc_trend, _, _ = btc_vane.get_btc_trend()
print(f"Main:{len(orch.cfg['scan_coins'])} Yaobi:{len(YAOBI_COINS)} Lightning:12 BTC:{btc_trend} MerCu:{'ON' if mercu.is_fresh() else 'STALE'}")
print("=" * 60)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

cycle = 0
while True:
    cycle += 1
    try:
        signal.alarm(90)
        t0 = time.time()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        # === Main strategy ===
        signals = orch.scanner.scan_all()

        # BTC vane filter
        for sig in signals:
            allowed, reason = btc_vane.filter(sig["symbol"], sig["direction"])
            if not allowed:
                sig["score"] = 0

        signals = [s for s in signals if s["score"] >= orch.cfg.get("signal_threshold", 25)]

        # === MerCu signals ===
        mercu_signals = mercu.get_coin_signals()
        for ms in mercu_signals[:5]:
            ms["ts"] = ts
            ms["cycle"] = cycle
            ms["source"] = "mercu"
            with open(MERUCU_LOG, "a") as f:
                f.write(json.dumps(ms) + "\n")
            print(f"  [{ts}] MERCU {ms['direction']:5s} {ms['symbol']:12s} Score:{ms['score']:+4d} {ms['reasons']}")

        # Log and print main signals
        for sig in signals:
            entry = {
                "ts": ts, "cycle": cycle, "source": "main",
                "symbol": sig["symbol"], "score": sig["score"],
                "direction": sig["direction"], "price": sig["price"],
                "filter_passed": True, "filter_reason": "passing",
                "details": sig.get("details", {}),
                "leading": sig.get("leading", []),
                "dag": sig.get("dag_consensus", "?"),
                "dag_score": sig.get("dag_score", 0),
                "btc_trend": btc_trend,
            }
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")

            launch_bonus = sig.get("launch_bonus", 0)
            launch_tag = f" Launch:+{launch_bonus}" if launch_bonus else ""
            print(f"  [{ts}] MAIN {sig['direction']:5s} {sig['symbol']:12s} "
                  f"Score:{sig['score']:+4d} ${sig['price']:.4f} DAG:{sig.get('dag_consensus', 0):+2d}{launch_tag}")

        # === Yaobi scan ===
        try:
            yaobi_signals = yaobi.scan_all()
            for ys in yaobi_signals[:5]:
                allowed, reason = btc_vane.filter(ys["symbol"], ys["direction"])
                if not allowed:
                    continue
                ye = {
                    "ts": ts, "cycle": cycle, "source": "yaobi",
                    "symbol": ys["symbol"], "score": ys["score"],
                    "direction": ys["direction"], "price": ys["price"],
                    "reasons": ys["reasons"]
                }
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
                fe = {
                    "ts": ts, "cycle": cycle, "source": "lightning",
                    "symbol": fs["symbol"], "score": fs["score"],
                    "direction": fs["direction"], "price": fs["price"],
                    "reasons": fs["reasons"]
                }
                with open(LIGHTNING_LOG, "a") as f:
                    f.write(json.dumps(fe) + "\n")
                print(f"  [{ts}] FLASH {fs['direction']:5s} {fs['symbol']:12s} "
                      f"Score:{fs['score']:+4d} ${fs['price']:.4f} {fs['reasons']}")
        except Exception as e:
            print(f"  [{ts}] FLASH error: {e}")

        signal.alarm(0)
        elapsed = time.time() - t0

        if not signals and not yaobi_signals and not flash_signals and not mercu_signals:
            print(f"  [{ts}] No signals (elapsed:{elapsed:.1f}s)")

        orch.state.set("last_scan", time.time())
        orch.state.save()

    except TimeoutError:
        print(f"  [{ts}] CYCLE TIMEOUT")
    except Exception as e:
        print(f"  [{ts}] CYCLE ERROR: {e}")
        time.sleep(5)

    time.sleep(max(0, orch.cfg.get("scan_interval", 60) - elapsed))
