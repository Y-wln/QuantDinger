with open("/home/ubuntu/scripts/agents/agent_orchestrator.py") as f:
    content = f.read()

# Replace btc_vane with tiered version
old_vane = """    def btc_vane(self):
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
            return ("unknown", True, True)"""

new_vane = """    # ??BTC???
    BTC_TIER1 = {"ETHUSDT","SOLUSDT","BNBUSDT","LINKUSDT","DOTUSDT","AVAXUSDT","LTCUSDT"}
    BTC_TIER2 = {"ADAUSDT","XRPUSDT","AAVEUSDT","APTUSDT"}
    # tier3: everything else (DOGE, FET, INJ, TRUMP, DASH etc) - no BTC filter

    def btc_vane(self, sym=None):
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

            if sym:
                if sym in self.BTC_TIER1:
                    # ????????BTC
                    return (trend, trend != "down", trend != "up")
                elif sym in self.BTC_TIER2:
                    # ????????????????
                    return (trend, True, True)  # allow both, score filter in process_signals
                else:
                    # ??/?????BTC??
                    return (trend, True, True)
            return (trend, trend != "down", trend != "up")
        except Exception:
            return ("unknown", True, True)"""

if old_vane in content:
    content = content.replace(old_vane, new_vane)
    print("btc_vane TIERED")
else:
    print("btc_vane PATTERN FAIL")

# Update process_signals to use per-symbol vane + tier2 score filter
old_ps_vane = """        # BTC???
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
                    continue"""

new_ps_vane = """        # BTC?????????
        btc_trend, _, _ = self.btc_vane()
        if btc_trend == "down":
            print("[" + time.strftime("%H:%M:%S") + "] BTC: ????")
        elif btc_trend == "up":
            print("[" + time.strftime("%H:%M:%S") + "] BTC: ????")
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
                # ??BTC?????
                _, allow_long, allow_short = self.btc_vane(sym)
                if direction == 'long' and not allow_long:
                    print("  BTC???[T1] ??" + sym + "??")
                    continue
                if direction == 'short' and not allow_short:
                    print("  BTC???[T1] ??" + sym + "??")
                    continue
                # Tier2: ??????
                if sym in self.BTC_TIER2:
                    if direction == 'long' and btc_trend == 'down' and abs_score < 55:
                        continue
                    if direction == 'short' and btc_trend == 'up' and abs_score < 55:
                        continue"""

if old_ps_vane in content:
    content = content.replace(old_ps_vane, new_ps_vane)
    print("process_signals TIERED")
else:
    print("process_signals PATTERN FAIL")

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(content)

import py_compile
try:
    py_compile.compile("/home/ubuntu/scripts/agents/agent_orchestrator.py", doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print("ERROR: " + str(e))
