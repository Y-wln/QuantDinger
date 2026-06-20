import sys, os
sys.path.insert(0, "/home/ubuntu/hermes-v2")
os.chdir("/home/ubuntu/hermes-v2")
from services.orchestrator import Orchestrator
print("Creating orch...")
o = Orchestrator()
print("Scorer type:", type(o.scorer).__name__)
print("Scanner coins:", len(o.cfg["scan_coins"]))
print("Running once...")
import signal as sig
def timeout_handler(signum, frame):
    raise TimeoutError("timeout")
sig.signal(sig.SIGALRM, timeout_handler)
sig.alarm(45)
try:
    signals = o.run_once()
    sig.alarm(0)
    print(f"Signals: {len(signals)}")
    for s in signals[:5]:
        print(f"  {s['direction']:5s} {s['symbol']:12s} score={s['score']:+4d} dag={s.get('dag_consensus', '?')}")
except TimeoutError:
    print("TIMEOUT - run_once hung")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback; traceback.print_exc()
