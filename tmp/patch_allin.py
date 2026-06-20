with open("/home/ubuntu/scripts/agents/agent_orchestrator.py") as f:
    content = f.read()

# ===== PATCH 1: process_signals (replace entire function) =====
old_ps = """    def process_signals(self, signals):
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

new_ps = """    def process_signals(self, signals):
        # BTC???
        btc_trend, allow_long, allow_short = self.btc_vane()
        if btc_trend == "down":
            print("[" + time.strftime("%H:%M:%S") + "] BTC???: ??, ????")
        elif btc_trend == "up":
            print("[" + time.strftime("%H:%M:%S") + "] BTC???: ??, ????")
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
                if abs(cvd) < 8 and abs_score < 45:
                    continue
                # BTC?????
                if direction == 'long' and not allow_long:
                    continue
                if direction == 'short' and not allow_short:
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
                    # Per-coin SL/TP
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
                        print('[' + time.strftime('%H:%M:%S') + '] SIGNAL ' + sym + ' ' + direction + ' score=' + str(score) + ' SL=' + str(round(sl_pct*100,1)) + '% TP=' + str(round(tp_pct*100,1)) + '%')
            except Exception:
                pass"""

if old_ps in content:
    content = content.replace(old_ps, new_ps)
    print("PATCH 1 OK: process_signals")
else:
    print("PATCH 1 FAIL")

# ===== PATCH 2: btc_vane before monitor_positions =====
old_mp = "    def monitor_positions(self):"
new_mp = """    def btc_vane(self):
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
            return (trend, trend != "down", trend != "up")
        except Exception:
            return ("unknown", True, True)

    def monitor_positions(self):"""

if old_mp in content:
    content = content.replace(old_mp, new_mp)
    print("PATCH 2 OK: btc_vane")
else:
    print("PATCH 2 FAIL")

# ===== PATCH 3: timeout BEFORE the SL if check =====
old_sl = "                if (direction=='long' and price<=p['sl']) or (direction=='short' and price>=p['sl']):"
new_sl = """                # ????
                timeout_exit = False
                timeout_reason = ""
                try:
                    ets = p.get("entry_time", "")
                    if ets:
                        from datetime import datetime as _dt2
                        ed = _dt2.strptime(ets, "%m-%d %H:%M")
                        nd = _dt2.now()
                        ed = ed.replace(year=nd.year)
                        hh = (nd - ed).total_seconds() / 3600
                        if hh < 0:
                            hh += 365 * 24
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
                        print("[" + time.strftime("%H:%M:%S") + "] CLOSE " + sym + " TIMEOUT PnL:" + str(round(result[2].get("pnl_pct", 0), 2)) + "%")
                elif (direction=='long' and price<=p['sl']) or (direction=='short' and price>=p['sl']):"""

if old_sl in content:
    content = content.replace(old_sl, new_sl)
    print("PATCH 3 OK: timeout")
else:
    print("PATCH 3 FAIL")

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(content)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print("COMPILE ERROR: " + str(e))
