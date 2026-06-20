f = open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "r")
lines = f.readlines()
f.close()

# 1. Find and replace process_signals
ps_start = -1
ps_end = -1
for i, line in enumerate(lines):
    if line.strip() == "def process_signals(self, signals):":
        ps_start = i
    if ps_start >= 0 and i > ps_start and line.strip().startswith("def "):
        ps_end = i
        break
if ps_end < 0:
    ps_end = len(lines)

print(f"process_signals: lines {ps_start+1}-{ps_end}")

new_ps = [
    "    def process_signals(self, signals):\n",
    "        # BTC???\n",
    "        btc_trend, allow_long, allow_short = self.btc_vane()\n",
    '        if btc_trend == "down":\n',
    '            print("[" + time.strftime("%H:%M:%S") + "] BTC???: ??, ????")\n',
    '        elif btc_trend == "up":\n',
    '            print("[" + time.strftime("%H:%M:%S") + "] BTC???: ??, ????")\n',
    "        signals.sort(key=lambda x: abs(x['score']), reverse=True)\n",
    "        for sig in signals:\n",
    "            try:\n",
    "                sym = sig['symbol']\n",
    "                direction = sig['signal']\n",
    "                score = sig['score']\n",
    "                price = sig['price']\n",
    "                cvd = sig.get('cvd1h', 0)\n",
    "                atr_val = sig.get('atr_val', 0)\n",
    "                if self.position.has_position(sym): continue\n",
    "                if len(self.position.get_positions()) >= MAX_POSITIONS: continue\n",
    "                ck = sym + '_' + direction\n",
    "                if ck in self.signal_cooldowns:\n",
    "                    if time.time() - self.signal_cooldowns[ck] < 900: continue\n",
    "                abs_score = abs(score)\n",
    "                if abs(cvd) < 8 and abs_score < 45:\n",
    "                    continue\n",
    "                # BTC?????\n",
    "                if direction == 'long' and not allow_long:\n",
    "                    continue\n",
    "                if direction == 'short' and not allow_short:\n",
    "                    continue\n",
    "                if 25 <= abs_score < 45:\n",
    "                    sig = self.leading_confirm(sig)\n",
    "                    score = score + sig.get('leading_bonus', 0)\n",
    "                    abs_score = abs(score)\n",
    "                    li = sig.get('leading_reasons', [])\n",
    "                    if li:\n",
    '                        print("  leading confirm " + sym + ": " + ",".join(li) + " final=" + str(score))\n',
    "                if abs_score >= SIGNAL_THRESHOLD:\n",
    "                    self.signal_cooldowns[ck] = time.time()\n",
    "                    # Per-coin SL/TP\n",
    "                    try:\n",
    "                        import json as _json\n",
    "                        with open('/home/ubuntu/scripts/agents/per_coin_params.json') as _f:\n",
    "                            pcp = _json.load(_f)\n",
    "                        if sym in pcp:\n",
    "                            sl_pct = pcp[sym]['sl_pct']\n",
    "                            tp_pct = pcp[sym]['tp_pct']\n",
    "                        elif atr_val > 0 and price > 0:\n",
    "                            ap = atr_val/price\n",
    "                            sl_pct = max(0.02, min(0.05, ap*2))\n",
    "                            tp_pct = max(0.03, min(0.08, ap*3))\n",
    "                        else:\n",
    "                            sl_pct = 0.03; tp_pct = 0.05\n",
    "                    except Exception:\n",
    "                        sl_pct = 0.03; tp_pct = 0.05\n",
    "                    ok, msg = self.position.open_position(sym, direction, price, score, cvd, sl_pct, tp_pct)\n",
    "                    if ok:\n",
    "                        r = sig.get('leading_reasons', [])\n",
    "                        self.position.notify_open(sym, direction, price, score, cvd, r[:3])\n",
    '                        print("[" + time.strftime("%H:%M:%S") + "] SIGNAL " + sym + " " + direction + " score=" + str(score) + " SL=" + str(round(sl_pct*100,1)) + "% TP=" + str(round(tp_pct*100,1)) + "%")\n',
    "            except Exception:\n",
    "                pass\n",
    "\n",
]

lines = lines[:ps_start] + new_ps + lines[ps_end:]

# 2. Add btc_vane before monitor_positions
mp_start = -1
for i, line in enumerate(lines):
    if line.strip() == "def monitor_positions(self):":
        mp_start = i
        break

btc_vane = [
    "\n",
    "    def btc_vane(self):\n",
    '        """BTC?????? (trend, allow_long, allow_short)"""\n',
    "        try:\n",
    '            k4 = self._4h_klines.get("BTCUSDT", [])\n',
    "            if not k4 or len(k4) < 50:\n",
    '                k4 = self.market.get_klines("BTCUSDT", "4h", 100)\n',
    '                if k4: self._4h_klines["BTCUSDT"] = k4\n',
    "            if len(k4) < 50:\n",
    '                return ("unknown", True, True)\n',
    "            from hermes_core import detect_structure\n",
    "            struct, _ = detect_structure(k4)\n",
    '            trend = "down" if struct == "down" else ("up" if struct == "up" else "neutral")\n',
    '            allow_long = trend != "down"\n',
    '            allow_short = trend != "up"\n',
    "            return (trend, allow_long, allow_short)\n",
    "        except Exception:\n",
    '            return ("unknown", True, True)\n',
    "\n",
]
lines = lines[:mp_start] + btc_vane + lines[mp_start:]

# 3. Add timeout exit in monitor_positions
# Find the line with SL check
sl_idx = -1
for i, line in enumerate(lines):
    if "price<=p['sl']" in line and "direction==" in line and "elif" not in line:
        sl_idx = i
        break

if sl_idx > 0:
    print(f"SL check at line {sl_idx+1}")
    timeout_lines = [
        "                # ????: 24h????, 8h??>1%??\n",
        "                timeout_exit = False\n",
        '                timeout_reason = ""\n',
        "                try:\n",
        '                    ets = p.get("entry_time", "")\n',
        "                    if ets:\n",
        "                        from datetime import datetime as _dt2\n",
        '                        ed = _dt2.strptime(ets, "%m-%d %H:%M")\n',
        "                        nd = _dt2.now()\n",
        "                        ed = ed.replace(year=nd.year)\n",
        "                        hh = (nd - ed).total_seconds() / 3600\n",
        "                        if hh < 0:\n",
        "                            hh += 365 * 24\n",
        "                        if hh > 24 and pp < 0.5:\n",
        "                            timeout_exit = True\n",
        '                            timeout_reason = "??24h"\n',
        "                        elif hh > 8 and pp < -1:\n",
        "                            timeout_exit = True\n",
        '                            timeout_reason = "??8h??>1%"\n',
        "                except Exception:\n",
        "                    pass\n",
        "\n",
        "                if timeout_exit:\n",
        "                    ok, msg, result = self.position.close_position(sym, price, timeout_reason)\n",
        "                    if ok and len(result) > 2:\n",
        '                        self.position.notify_close(sym, ("close", "", result[2]))\n',
        '                        print("[" + time.strftime("%H:%M:%S") + "] CLOSE " + sym + " TIMEOUT PnL:" + str(round(result[2].get("pnl_pct", 0), 2)) + "%")\n',
        "                el" + lines[sl_idx].lstrip()[2:],  # 'elif ...' preserves the elif
    ]
    lines = lines[:sl_idx] + timeout_lines + lines[sl_idx+1:]
else:
    print("WARN: SL check not found")

f = open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w")
f.writelines(lines)
f.close()

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
    print("ALL PATCHES APPLIED + COMPILES OK")
except py_compile.PyCompileError as e:
    print("ERROR: " + str(e))
