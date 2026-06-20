import sys, traceback
sys.path.insert(0, '/home/ubuntu/hermes-v2')

print("1. Testing core imports...")
try:
    from core.http_client import HTTPClient
    print("   http_client OK")
    from core.exchange import ExchangeAPI
    print("   exchange OK")
    from core.klines import KlineCache
    print("   klines OK")
    from core.config_loader import load_config
    print("   config_loader OK")
    from core.alerts import Alerts
    print("   alerts OK")
    from core.state import State
    print("   state OK")
    from core.decision_log import DecisionLog
    print("   decision_log OK")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

print("2. Testing indicator imports...")
try:
    from indicators.scorer import Scorer
    print("   scorer OK")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

print("3. Testing service imports...")
try:
    from services.scanner import Scanner
    print("   scanner OK")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

try:
    from services.filter import Filter
    print("   filter OK")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

try:
    from services.trader import Trader
    print("   trader OK")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

try:
    from services.monitor import Monitor
    print("   monitor OK")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

try:
    from services.safety import Safety
    print("   safety OK")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

print("4. Testing orchestrator import...")
try:
    from services.orchestrator import Orchestrator
    print("   orchestrator OK")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

print("Done!")
