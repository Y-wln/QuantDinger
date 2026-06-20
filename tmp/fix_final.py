f = open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "r")
lines = f.readlines()
f.close()

# Find the line number of the SL check
target = -1
for i, line in enumerate(lines):
    if "price<=p['sl']" in line and "direction==" in line and "elif" in line:
        target = i
        break

if target < 0:
    target = -1
    for i, line in enumerate(lines):
        if "price<=p['sl']" in line and "direction==" in line:
            target = i
            break

if target < 0:
    print("CANNOT FIND TARGET LINE")
else:
    print(f"Found at line {target+1}: {lines[target].strip()[:80]}")

    timeout_lines = [
        '                # ????: 24h????, 8h??>1%??\n',
        '                timeout_exit = False\n',
        '                timeout_reason = ""\n',
        '                try:\n',
        '                    ets = p.get("entry_time", "")\n',
        '                    if ets:\n',
        '                        from datetime import datetime as _dt2\n',
        '                        ed = _dt2.strptime(ets, "%m-%d %H:%M")\n',
        '                        nd = _dt2.now()\n',
        '                        ed = ed.replace(year=nd.year)\n',
        '                        hh = (nd - ed).total_seconds() / 3600\n',
        '                        if hh < 0:\n',
        '                            hh += 365 * 24\n',
        '                        if hh > 24 and pp < 0.5:\n',
        '                            timeout_exit = True\n',
        '                            timeout_reason = "??24h"\n',
        '                        elif hh > 8 and pp < -1:\n',
        '                            timeout_exit = True\n',
        '                            timeout_reason = "??8h??>1%"\n',
        '                except Exception:\n',
        '                    pass\n',
        '\n',
        '                if timeout_exit:\n',
        '                    ok, msg, result = self.position.close_position(sym, price, timeout_reason)\n',
        '                    if ok and len(result) > 2:\n',
        '                        self.position.notify_close(sym, ("close", "", result[2]))\n',
        '                        print("[" + time.strftime("%H:%M:%S") + "] CLOSE " + sym + " TIMEOUT PnL:" + str(round(result[2].get("pnl_pct", 0), 2)) + "%")\n',
        '                el' + lines[target].lstrip()[2:],  # 'elif ...' 
    ]
    
    new_lines = lines[:target] + timeout_lines + lines[target+1:]
    
    f = open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w")
    f.writelines(new_lines)
    f.close()
    
    import py_compile
    try:
        py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
        print("[OK] compiles successfully")
    except py_compile.PyCompileError as e:
        print("[ERROR] " + str(e))
