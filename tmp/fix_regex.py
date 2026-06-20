import re

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "r") as f:
    content = f.read()

# Match the exact pattern before the SL check
# Find: "                if (direction==.long. and price<=p[.sl.])"
pattern = r'(                )(if \(direction==.long. and price<=p\[.sl.\]\))'
replacement = r'''                # ????
                timeout_exit = False
                timeout_reason = ""
                try:
                    ets = p.get("entry_time", "")
                    if ets:
                        from datetime import datetime as _dt2
                        ed = _dt2.strptime(ets, "%%m-%%d %%H:%%M")
                        nd = _dt2.now()
                        ed = ed.replace(year=nd.year)
                        hh = (nd - ed).total_seconds() / 3600
                        if hh < 0: hh += 365 * 24
                        if hh > 24 and pp < 0.5:
                            timeout_exit = True
                            timeout_reason = "??24h"
                        elif hh > 8 and pp < -1:
                            timeout_exit = True
                            timeout_reason = "??8h??>1%"
                except Exception:
                    pass

                if timeout_exit:
                    ok, msg, result = self.position.close_position(sym, price, timeout_reason)
                    if ok and len(result) > 2:
                        self.position.notify_close(sym, ("close", "", result[2]))
                        print("[" + time.strftime("%%H:%%M:%%S") + "] CLOSE " + sym + " TIMEOUT PnL:" + str(round(result[2].get("pnl_pct", 0), 2)) + "%%")
                el\2'''

# The %% are for the Python format string, they'll become % in the actual replacement
replacement = replacement.replace("%%H:%%M:%%S", "%H:%M:%S")
replacement = replacement.replace("%%m-%%d %%H:%%M", "%m-%d %H:%M")
replacement = replacement.replace("%%", "%")

new_content = re.sub(pattern, replacement, content)
if new_content != content:
    print("Pattern matched and replaced")
else:
    print("Pattern NOT matched")
    
with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(new_content)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
    print("[OK] compiles")
except py_compile.PyCompileError as e:
    print("[ERROR] " + str(e))
