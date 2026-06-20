with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "r") as f:
    code = f.read()

# 1. More aggressive timeout thresholds
code = code.replace(
    "if hours_held > 24 and pp < 1:",
    "if hours_held > 24 and pp < 0.5:"
)
code = code.replace(
    "elif hours_held > 12 and pp < -2:",
    "elif hours_held > 8 and pp < -1:"
)
code = code.replace(
    'timeout_reason = "??12h??>2%"',
    'timeout_reason = "??8h??>1%"'
)

# 2. Add BTC vane debug
code = code.replace(
    "btc_trend, allow_long, allow_short = self.btc_vane()",
    "btc_trend, allow_long, allow_short = self.btc_vane()\n        if btc_trend == 'down':\n            print('[' + time.strftime('%H:%M:%S') + '] BTC???: ????, ????')\n        elif btc_trend == 'up':\n            print('[' + time.strftime('%H:%M:%S') + '] BTC???: ????, ????')"
)

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(code)

import py_compile
py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
print("[OK] thresholds tightened + debug added")
