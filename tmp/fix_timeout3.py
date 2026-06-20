with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "r") as f:
    lines = f.readlines()

# Find the line with "if (direction=='long' and price<=p['sl'])"
target_idx = -1
for i, line in enumerate(lines):
    if "if (direction=='long' and price<=p['sl'])" in line:
        target_idx = i
        print(f"Found at line {i+1}: {line.strip()[:60]}")
        break

if target_idx < 0:
    print("NOT FOUND")
else:
    timeout_block = [
        "                # ?????24h?????8h??>1%??\n",
        "                timeout_exit = False\n",
        "                timeout_reason = \"\"\n",
        "                try:\n",
        "                    entry_time_str = p.get(\"entry_time\", \"\")\n",
        "                    if entry_time_str:\n",
        "                        from datetime import datetime as _dt\n",
        "                        entry_dt = _dt.strptime(entry_time_str, \"%m-%d %H:%M\")\n",
        "                        now_dt = _dt.now()\n",
        "                        entry_dt = entry_dt.replace(year=now_dt.year)\n",
        "                        hours_held = (now_dt - entry_dt).total_seconds() / 3600\n",
        "                        if hours_held < 0:\n",
        "                            hours_held += 365 * 24\n",
        "                        if hours_held > 24 and pp < 0.5:\n",
        "                            timeout_exit = True\n",
        "                            timeout_reason = \"??24h\"\n",
        "                        elif hours_held > 8 and pp < -1:\n",
        "                            timeout_exit = True\n",
        "                            timeout_reason = \"??8h??>1%\"\n",
        "                except Exception:\n",
        "                    pass\n",
        "\n",
        "                if timeout_exit:\n",
        "                    ok, msg, result = self.position.close_position(sym, price, timeout_reason)\n",
        "                    if ok and len(result) > 2:\n",
        "                        self.position.notify_close(sym, (\"close\", \"\", result[2]))\n",
        "                        print(\"[\" + time.strftime(\"%H:%M:%S\") + \"] CLOSE \" + sym + \" TIMEOUT PnL:\" + str(round(result[2].get(\"pnl_pct\", 0), 2)) + \"%\")\n",
        "                el",
    ]
    # Insert before the if line
    new_lines = lines[:target_idx] + timeout_block + [lines[target_idx][2:]]  # remove 'el' prefix from original
    # Actually let me keep it simpler
    new_lines = lines[:target_idx] + timeout_block
    new_lines.append(lines[target_idx].replace("if (direction==", "elif (direction==", 1))

    with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
        f.writelines(new_lines)

    import py_compile
    py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
    print("[OK] timeout inserted and compiles")
