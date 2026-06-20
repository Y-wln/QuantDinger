# -*- coding: utf-8 -*-
import json

# Per-coin optimized SL/TP based on 180-day backtest volatility
# SL?TP??ATR????????????
PER_COIN_PARAMS = {
    # ??? - ?????
    "BTCUSDT": {"sl_pct": 0.03, "tp_pct": 0.05},
    "ETHUSDT": {"sl_pct": 0.03, "tp_pct": 0.05},
    "SOLUSDT": {"sl_pct": 0.03, "tp_pct": 0.05},
    "ADAUSDT": {"sl_pct": 0.03, "tp_pct": 0.05},
    "DOGEUSDT": {"sl_pct": 0.04, "tp_pct": 0.06},  # meme????
    "LINKUSDT": {"sl_pct": 0.03, "tp_pct": 0.05},
    "APTUSDT": {"sl_pct": 0.035, "tp_pct": 0.06},
    "AAVEUSDT": {"sl_pct": 0.03, "tp_pct": 0.05},
    "DOTUSDT": {"sl_pct": 0.035, "tp_pct": 0.06},

    # ??? - ??????
    "BNBUSDT": {"sl_pct": 0.045, "tp_pct": 0.07},   # ????(37?)??????
    "AVAXUSDT": {"sl_pct": 0.04, "tp_pct": 0.065},   # ?????????
    "XRPUSDT": {"sl_pct": 0.05, "tp_pct": 0.08},     # ?????????
    "LTCUSDT": {"sl_pct": 0.045, "tp_pct": 0.07},    # ?????
    "FETUSDT": {"sl_pct": 0.05, "tp_pct": 0.08},     # ???????
    "INJUSDT": {"sl_pct": 0.055, "tp_pct": 0.09},    # ?????????
}

with open("/home/ubuntu/scripts/agents/per_coin_params.json", "w") as f:
    json.dump(PER_COIN_PARAMS, f, indent=2)
print("per_coin_params.json written")

# Now patch agent_orchestrator to use per-coin params
with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "r") as f:
    code = f.read()

# Find the open_position call in process_signals
old_sl_tp = """                if atr_val > 0 and price > 0:
                        ap = atr_val/price
                        sl_pct = max(0.02, min(0.05, ap*2))
                        tp_pct = max(0.03, min(0.08, ap*3))
                    else:
                        sl_pct = 0.03; tp_pct = 0.05"""

new_sl_tp = """                # Per-coin optimized SL/TP (fallback to ATR-based)
                try:
                    import json as _json
                    with open('/home/ubuntu/scripts/agents/per_coin_params.json') as _f:
                        pcp = _json.load(_f)
                    if sym in pcp:
                        sl_pct = pcp[sym]['sl_pct']
                        tp_pct = pcp[sym]['tp_pct']
                    elif atr_val > 0 and price > 0:
                        ap = atr_val/price
                        sl_pct = max(0.02, min(0.05, ap*2))
                        tp_pct = max(0.03, min(0.08, ap*3))
                    else:
                        sl_pct = 0.03; tp_pct = 0.05
                except Exception:
                    sl_pct = 0.03; tp_pct = 0.05"""

if old_sl_tp in code:
    code = code.replace(old_sl_tp, new_sl_tp)
    print("[OK] Per-coin SL/TP patched into orchestrator")
else:
    print("[WARN] Pattern not found, checking...")
    # Try alternative
    if "per_coin_params" in code:
        print("[SKIP] Already patched")

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(code)

import py_compile
py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
print("[OK] agent_orchestrator compiles")
