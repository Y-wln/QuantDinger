with open("/home/ubuntu/scripts/agents/agent_orchestrator.py") as f:
    content = f.read()

# Insert BTC vane call at start of process_signals
old_start = """    def process_signals(self, signals):
        signals.sort(key=lambda x: abs(x['score']), reverse=True)"""

new_start = """    def process_signals(self, signals):
        # BTC?????????
        btc_trend, _, _ = self.btc_vane()
        if btc_trend == "down":
            print("[" + time.strftime("%H:%M:%S") + "] BTC???: ??")
        elif btc_trend == "up":
            print("[" + time.strftime("%H:%M:%S") + "] BTC???: ??")
        signals.sort(key=lambda x: abs(x['score']), reverse=True)"""

if old_start in content:
    content = content.replace(old_start, new_start)
    print("BTC vane call inserted into process_signals")
else:
    print("PATTERN FAIL")

# Now add the per-signal vane filter after the CVD check
old_filter = """                if abs(cvd) < 8 and abs_score < 45:
                    continue
                if 25 <= abs_score < 45:"""

new_filter = """                if abs(cvd) < 8 and abs_score < 45:
                    continue
                # ??BTC???
                _, allow_long, allow_short = self.btc_vane(sym)
                if direction == 'long' and not allow_long:
                    continue
                if direction == 'short' and not allow_short:
                    continue
                # Tier2?????
                if sym in self.BTC_TIER2:
                    if direction == 'long' and btc_trend == 'down' and abs_score < 55:
                        continue
                    if direction == 'short' and btc_trend == 'up' and abs_score < 55:
                        continue
                if 25 <= abs_score < 45:"""

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    print("Tier filter inserted")
else:
    print("Tier filter FAIL")

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(content)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print("ERROR: " + str(e))
