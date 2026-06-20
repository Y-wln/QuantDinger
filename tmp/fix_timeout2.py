with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "r") as f:
    code = f.read()

# Find the exact line that starts with "                if (direction=='long' and price<=p['sl'])"
# and insert timeout code BEFORE it
old_line = "                if (direction=='long'"
new_block = """                # ?????24h?????8h??>1%??
                timeout_exit = False
                timeout_reason = ""
                try:
                    entry_time_str = p.get("entry_time", "")
                    if entry_time_str:
                        from datetime import datetime as _dt
                        entry_dt = _dt.strptime(entry_time_str, "%m-%d %H:%M")
                        now_dt = _dt.now()
                        entry_dt = entry_dt.replace(year=now_dt.year)
                        hours_held = (now_dt - entry_dt).total_seconds() / 3600
                        if hours_held < 0:
                            hours_held += 365 * 24
                        if hours_held > 24 and pp < 0.5:
                            timeout_exit = True
                            timeout_reason = "??24h"
                        elif hours_held > 8 and pp < -1:
                            timeout_exit = True
                            timeout_reason = "??8h??>1%"
                except Exception:
                    pass

                if timeout_exit:
                    ok, msg, result = self.position.close_position(sym, price, timeout_reason)
                    if ok and len(result) > 2:
                        self.position.notify_close(sym, ("close", "", result[2]))
                        print("[" + time.strftime("%H:%M:%S") + "] CLOSE " + sym + " TIMEOUT PnL:" + str(round(result[2].get("pnl_pct", 0), 2)) + "%")
                elif (direction=='long'"""

code = code.replace(old_line, new_block)

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
    print("[OK] timeout exit added + compiles")
except py_compile.PyCompileError as e:
    print("[ERROR] " + str(e))
