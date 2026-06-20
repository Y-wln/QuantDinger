import sys, os, time
sys.path.insert(0, "/home/ubuntu/hermes-v2")
os.chdir("/home/ubuntu/hermes-v2")

steps = [
    ("load_config", "from core.config_loader import load_config"),
    ("HTTPClient", "from core.http_client import HTTPClient"),
    ("ExchangeAPI", "from core.exchange import ExchangeAPI"),
    ("KlineCache", "from core.klines import KlineCache"),
    ("Alerts", "from core.alerts import Alerts"),
    ("State", "from core.state import State"),
    ("DecisionLog", "from core.decision_log import DecisionLog"),
    ("ScorerV2", "from indicators.scorer_v2 import ScorerV2"),
    ("Scanner", "from services.scanner import Scanner"),
    ("Filter", "from services.filter import Filter"),
    ("Trader", "from services.trader import Trader"),
    ("Monitor", "from services.monitor import Monitor"),
    ("Safety", "from services.safety import Safety"),
    ("DAGConsensus", "from services.dag import DAGConsensus"),
    ("Jin10Bridge", "from services.jin10 import Jin10Bridge"),
]

for name, import_stmt in steps:
    t0 = time.time()
    try:
        exec(import_stmt)
        elapsed = time.time() - t0
        print(f"OK {name} ({elapsed:.1f}s)")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"FAIL {name} ({elapsed:.1f}s): {e}")

# Now try construct each
print("\n--- Constructing ---")
cfg = load_config()
print("Config loaded. scorer_version:", cfg.get("scorer_version", "v1"))
http = HTTPClient(retries=cfg["api_retries"], timeout=cfg["api_timeout"])
print("HTTP client ok")
ex = ExchangeAPI(http)
print("Exchange ok")
kc = KlineCache(ex)
print("KlineCache ok")
alerts = Alerts(webhook_url=cfg.get("feishu_webhook"), log_dir=cfg.get("log_dir"))
print("Alerts ok")
state = State(cfg.get("data_dir", "") + "/state.json")
print("State ok")
dlog = DecisionLog(cfg.get("log_dir"))
print("DecisionLog ok")
scorer = ScorerV2()
print("ScorerV2 ok")
scanner = Scanner(cfg, kc, scorer, alerts, dlog)
print("Scanner ok")
filt = Filter(cfg, state, alerts, dlog)
print("Filter ok")
trader = Trader(cfg, ex, state, alerts, dlog)
print("Trader ok")
monitor = Monitor(cfg, ex, state, trader, alerts)
print("Monitor ok")
safety = Safety(cfg, state, alerts)
print("Safety ok")
dag = DAGConsensus()
print("DAG ok")
jin10 = Jin10Bridge()
print("Jin10 ok - ALL DONE")
