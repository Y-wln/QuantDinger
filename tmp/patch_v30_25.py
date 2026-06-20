import sys, re

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "r") as f:
    code = f.read()

# ============================================
# 1. Add BTC??? check method
# ============================================
btc_vane_method = '''
    def btc_vane(self):
        """BTC?????? (trend, allow_long, allow_short)"""
        try:
            k4 = self._4h_klines.get("BTCUSDT", [])
            if not k4 or len(k4) < 50:
                k4 = self.market.get_klines("BTCUSDT", "4h", 100)
                if k4: self._4h_klines["BTCUSDT"] = k4
            if len(k4) < 50:
                return ("unknown", True, True)
            from hermes_core import detect_structure
            struct, _ = detect_structure(k4)
            trend = "down" if struct == "down" else ("up" if struct == "up" else "neutral")
            # BTC???????????BTC???????
            allow_long = trend != "down"
            allow_short = trend != "up"
            return (trend, allow_long, allow_short)
        except Exception:
            return ("unknown", True, True)
'''

# Insert before monitor_positions
insert_point = code.find("    def monitor_positions")
if insert_point > 0 and "def btc_vane" not in code:
    code = code[:insert_point] + btc_vane_method + "\n" + code[insert_point:]
    print("[OK] btc_vane added")
else:
    print("[SKIP] btc_vane exists")

# ============================================
# 2. Add ???? to monitor_positions
# ============================================
old_timeout_check = """                if (direction=='long' and price<=p['sl']) or (direction=='short' and price>=p['sl']):
                    ok, msg, result = self.position.close_position(sym, price, '??')"""

new_timeout_check = """                # ?????24h??????12h??>2%??
                entry_time_str = p.get("entry_time", "")
                timeout_exit = False
                timeout_reason = ""
                try:
                    if entry_time_str:
                        entry_dt = datetime.strptime(entry_time_str, "%m-%d %H:%M")
                        now_dt = datetime.now()
                        hours_held = (now_dt - entry_dt.replace(year=now_dt.year)).total_seconds() / 3600
                        if hours_held < 0:
                            hours_held += 365 * 24  # crossed year boundary
                        if hours_held > 24 and pp < 1:
                            timeout_exit = True
                            timeout_reason = "??24h"
                        elif hours_held > 12 and pp < -2:
                            timeout_exit = True
                            timeout_reason = "??12h??>2%"
                except Exception:
                    pass

                if timeout_exit:
                    ok, msg, result = self.position.close_position(sym, price, timeout_reason)
                    if ok and len(result) > 2:
                        self.position.notify_close(sym, ("close", "", result[2]))
                        print("[" + time.strftime("%H:%M:%S") + "] CLOSE " + sym + " TIMEOUT PnL:" + str(round(result[2].get("pnl_pct", 0), 2)) + "%")
                elif (direction=='long' and price<=p['sl']) or (direction=='short' and price>=p['sl']):
                    ok, msg, result = self.position.close_position(sym, price, '??')"""

code = code.replace(old_timeout_check, new_timeout_check)
print("[OK] timeout exit added")

# ============================================
# 3. Fix process_signals: indentation + BTC vane
# ============================================
old_process = """    def process_signals(self, signals):
        signals.sort(key=lambda x: abs(x['score']), reverse=True)
        for sig in signals:
            try:
                sym = sig['symbol']
                direction = sig['signal']
                score = sig['score']
                price = sig['price']
                cvd = sig.get('cvd1h', 0)
                atr_val = sig.get('atr_val', 0)
                if self.position.has_position(sym): continue
                if len(self.position.get_positions()) >= MAX_POSITIONS: continue
                ck = sym + '_' + direction
                if ck in self.signal_cooldowns:
                    if time.time() - self.signal_cooldowns[ck] < 900: continue
                abs_score = abs(score)
                # CVD??????????????
                if abs(cvd) < 8 and abs_score < 45:
                    continue
                if 25 <= abs_score < 45:
                    sig = self.leading_confirm(sig)
                    score = score + sig.get('leading_bonus', 0)
                    abs_score = abs(score)
                    li = sig.get('leading_reasons', [])
                    if li:
                        print('  leading confirm ' + sym + ': ' + ','.join(li) + ' final=' + str(score))
                if abs_score >= SIGNAL_THRESHOLD:
                    self.signal_cooldowns[ck] = time.time()
                    # Per-coin optimized SL/TP (fallback to ATR-based)
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
                    sl_pct = 0.03; tp_pct = 0.05
                    ok, msg = self.position.open_position(sym, direction, price, score, cvd, sl_pct, tp_pct)
                    if ok:
                        r = sig.get('leading_reasons', [])
                        self.position.notify_open(sym, direction, price, score, cvd, r[:3])
                        print('['+time.strftime('%H:%M:%S')+'] SIGNAL '+sym+' '+direction+' score='+str(score)+' SL='+str(round(sl_pct*100,1))+'% TP='+str(round(tp_pct*100,1))+'%')
            except Exception:
                pass"""

new_process = """    def process_signals(self, signals):
        # BTC??????????????
        btc_trend, allow_long, allow_short = self.btc_vane()
        signals.sort(key=lambda x: abs(x['score']), reverse=True)
        for sig in signals:
            try:
                sym = sig['symbol']
                direction = sig['signal']
                score = sig['score']
                price = sig['price']
                cvd = sig.get('cvd1h', 0)
                atr_val = sig.get('atr_val', 0)
                if self.position.has_position(sym): continue
                if len(self.position.get_positions()) >= MAX_POSITIONS: continue
                ck = sym + '_' + direction
                if ck in self.signal_cooldowns:
                    if time.time() - self.signal_cooldowns[ck] < 900: continue
                abs_score = abs(score)
                # CVD??????????????
                if abs(cvd) < 8 and abs_score < 45:
                    continue
                # BTC?????
                if direction == 'long' and not allow_long:
                    print('  BTC???[' + btc_trend + '] ??' + sym + '??')
                    continue
                if direction == 'short' and not allow_short:
                    print('  BTC???[' + btc_trend + '] ??' + sym + '??')
                    continue
                if 25 <= abs_score < 45:
                    sig = self.leading_confirm(sig)
                    score = score + sig.get('leading_bonus', 0)
                    abs_score = abs(score)
                    li = sig.get('leading_reasons', [])
                    if li:
                        print('  leading confirm ' + sym + ': ' + ','.join(li) + ' final=' + str(score))
                if abs_score >= SIGNAL_THRESHOLD:
                    self.signal_cooldowns[ck] = time.time()
                    # Per-coin optimized SL/TP
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
                        sl_pct = 0.03; tp_pct = 0.05
                    ok, msg = self.position.open_position(sym, direction, price, score, cvd, sl_pct, tp_pct)
                    if ok:
                        r = sig.get('leading_reasons', [])
                        self.position.notify_open(sym, direction, price, score, cvd, r[:3])
                        print('['+time.strftime('%H:%M:%S')+'] SIGNAL '+sym+' '+direction+' score='+str(score)+' SL='+str(round(sl_pct*100,1))+'% TP='+str(round(tp_pct*100,1))+'%')
            except Exception:
                pass"""

if old_process in code:
    code = code.replace(old_process, new_process)
    print("[OK] process_signals fixed + BTC vane integrated")
else:
    print("[FAIL] process_signals pattern not found - trying line-based approach")
    # Fallback: find the function boundaries and replace
    lines = code.split("\n")
    start = -1
    end = -1
    for i, line in enumerate(lines):
        if line.strip() == "def process_signals(self, signals):":
            start = i
        if start >= 0 and line.strip().startswith("def ") and i > start:
            end = i
            break
    if start >= 0 and end < 0:
        end = len(lines)
    if start >= 0:
        old_func = "\n".join(lines[start:end])
        new_func_lines = new_process.split("\n")
        result_lines = lines[:start] + new_func_lines + lines[end:]
        code = "\n".join(result_lines)
        print(f"[OK] process_signals replaced via line-based (lines {start}-{end})")
    else:
        print("[FATAL] cannot find process_signals")

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
    print("[OK] compiles successfully")
except py_compile.PyCompileError as e:
    print("[ERROR] " + str(e))
