# yaobi_pusher.py v14.0 - v13 + minimum signal quality gate: >=2 confirmations required
import sys, os, time, json
sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import (fetch_klines, fetch_price, fetch_funding_rate,
                         fetch_fear_greed, feishu_app_send, calc_cvd,
                         fetch_orderbook_imbalance)
from agent_technical import TechnicalAgent
from mercu_validator import validate_signal
from cross_validate import write_signals, get_badge
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))
BASE_COINS = ["CHZUSDT","IOUSDT","TONUSDT","STRAXUSDT","SENTUSDT","ENAUSDT","UNIUSDT",
    "TAOUSDT","ONDOUSDT","PUMPUSDT","ALLOUSDT","NEARUSDT","INJUSDT",
    "APTUSDT","FETUSDT","AAVEUSDT","TRUMPUSDT","DASHUSDT","ZECUSDT","WLDUSDT","HYPEUSDT",
    "STGUSDT","AIOUSDT","PLAYUSDT","SYNUSDT","PORTALUSDT","OPENUSDT","COAIUSDT"]

def get_dynamic_coins():
    """v8: Expand coin list with mercu anomaly coins"""
    coins = list(BASE_COINS)
    try:
        import json, os
        anom_path = "/home/ubuntu/scripts/agents/mercu_data/anomaly-v4.json"
        if os.path.exists(anom_path):
            with open(anom_path) as f:
                anom = json.load(f)
            for a in anom.get("data", []):
                sym = str(a.get("symbol", "")).upper()
                usdt_sym = sym + "USDT"
                if usdt_sym not in coins:
                    coins.append(usdt_sym)
            for sa in anom.get("state_anomalies", []):
                sym = str(sa.get("symbol", "")).upper()
                usdt_sym = sym + "USDT"
                if usdt_sym not in coins:
                    coins.append(usdt_sym)
    except:
        pass
    return coins
CHAT_ID = "oc_58c90b36ddb0d64439c64ed83a16b47b"

# === v6: state tracking ===
_cooldowns = {}    # {sym_dir: last_push_ts}
_last_dir = {}     # {sym: last_direction}
_streaks = {}      # {sym_dir: consecutive_count}

print("[YaobiPusher v14 FULL] starting...")
feishu_app_send("Yaobi Pusher v14 | gate>=3-confirms +OB-final +no-chase +choppy | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT_ID)

_ta = TechnicalAgent()

def atr(klines, period=14):
    if len(klines) < period + 1: return 0
    trs = []
    for i in range(-period, 0):
        h, l, pc = klines[i]["h"], klines[i]["l"], klines[i-1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs) / len(trs)

def yaobi_vote(k5, k15, k1, funding_rate, ob_imb=None):
    """
    v6: 妖币专属投票
    - CVD权重 1.5→2.0
    - 去掉1h CVD背离（太慢）
    - 加盘口失衡第6票
    - 加动量加速度
    """
    vl = 0.0; vs = 0.0
    rl = []; rs = []
    if not k5 or len(k5) < 10: return None, 0, [], []
    
    cv5 = calc_cvd(k5, 3)
    # === Vote 1: 5m CVD (v6: 权重2.0) ===
    if cv5 > 30: vl += 2.0; rl.append("5mCVD_buy(%d%%)" % int(cv5))
    elif cv5 < -30: vs += 2.0; rs.append("5mCVD_sell(%d%%)" % int(abs(cv5)))
    elif cv5 > 15: vl += 1.0; rl.append("5mCVD_buy(%d%%)" % int(cv5))
    elif cv5 < -15: vs += 1.0; rs.append("5mCVD_sell(%d%%)" % int(abs(cv5)))
    
    p3 = (k5[-1]["c"] - k5[-3]["c"]) / k5[-3]["c"] * 100 if k5[-3]["c"] > 0 else 0
    p6 = (k5[-1]["c"] - k5[-6]["c"]) / k5[-6]["c"] * 100 if len(k5)>=7 else 0
    g = sum(1 for i in range(-3,0) if k5[i]["c"] > k5[i]["o"])
    
    # === Vote 2: 价格动量 ===
    if g >= 3 and p3 > 0.2: vl += 1; rl.append("3green_%.2f%%" % p3)
    elif g == 0 and p3 < -0.2: vs += 1; rs.append("3red_%.2f%%" % abs(p3))
    elif p3 > 0.2: vl += 0.5
    elif p3 < -0.2: vs += 0.5
    
    # === Vote 3: 成交量爆发 (v6: 阈值降到1.5x) ===
    if len(k5) >= 6:
        vr = sum(k5[i]["v"] for i in range(-3, 0))
        vp = max(sum(k5[i]["v"] for i in range(-6, -3)), 0.001)
        ratio = vr / vp
        if ratio > 1.5 and p3 > 0: vl += 1; rl.append("vol%.1fx_up" % ratio)
        elif ratio > 1.5 and p3 < 0: vs += 1; rs.append("vol%.1fx_down" % ratio)
    
    # === Vote 4: 15m CVD ===
    if k15 and len(k15) >= 6:
        cv15 = calc_cvd(k15, 3)
        if cv15 > 20: vl += 1; rl.append("15mCV_%d%%" % int(cv15))
        elif cv15 < -20: vs += 1; rs.append("15mCV_%d%%" % int(abs(cv15)))
    
    # === Vote 5: 动量加速度 (v6新增，替代1h背离) ===
    if len(k5) >= 12:
        mom_recent = (k5[-1]["c"] - k5[-6]["c"]) / k5[-6]["c"] * 100 if k5[-6]["c"] > 0 else 0
        mom_prev = (k5[-6]["c"] - k5[-12]["c"]) / k5[-12]["c"] * 100 if k5[-12]["c"] > 0 else 0
        if mom_recent > 0.5 and mom_recent > mom_prev: vl += 1; rl.append("mom_accel")
        elif mom_recent < -0.5 and mom_recent < mom_prev: vs += 1; rs.append("mom_accel_down")
    
    # === Vote 6: 盘口失衡 (v6新增) ===
    if ob_imb is not None:
        imb = ob_imb.get("imbalance", 0)  # positive = bid heavy
        ratio = ob_imb.get("ratio", 1.0)
        if imb > 15: vl += 0.5; rl.append("bid_wall(%d%%)" % int(imb))
        elif imb < -15: vs += 0.5; rs.append("ask_wall(%d%%)" % int(abs(imb)))
    
    # === v11: OB-CVD conflict - OB is forward-looking, trust over CVD ===
    if ob_imb is not None:
        imb = ob_imb.get("imbalance", 0)
        if imb > 20 and vs > vl:
            vl = vs + 1.0
            rl.append("OB_flip_long(%d%%)" % int(imb))
            rs = []
        elif imb < -20 and vl > vs:
            vs = vl + 1.0
            rs.append("OB_flip_short(%d%%)" % int(abs(imb)))
            rl = []
    # === 费率 bonus ===
    if funding_rate < -0.001: vl += 0.5; rl.append("fr_short")
    elif funding_rate > 0.001: vs += 0.5; rs.append("fr_long")
    
    # === Vote 7: MerCu OI?? (v8) ===
    try:
        from mercu_validator import validate_signal
        sym_root = k5[0].get("s","").replace("USDT","") if k5 else ""
        if sym_root:
            m = validate_signal(sym_root, "long" if vl > vs else "short")
            if m and m.get("bonus", 0) > 0:
                if vl > vs: vl += 0.5; rl.append("OI_confirm")
                else: vs += 0.5; rs.append("OI_confirm")
            elif m and m.get("bonus", 0) < 0:
                if vl > vs: vs += 0.5; rs.append("OI_warn")
                else: vl += 0.5; rl.append("OI_warn")
    except:
        pass
    
    if vl >= 2.5: return "long", vl, rl, rs
    if vs >= 2.5: return "short", vs, rl, rs
    return None, 0, rl, rs

def price_gatekeeper(direction, k5):
    if not k5 or len(k5) < 6: return True, ""
    pct = (k5[-1]["c"] - k5[-6]["c"]) / k5[-6]["c"] * 100
    if direction == "long" and pct < -1.0: return False, "falling_%.1f%%" % abs(pct)
    if direction == "short" and pct > 1.0: return False, "rising_%.1f%%" % pct
    return True, ""

while True:
    try:
        t0 = time.time()
        fng = fetch_fear_greed()
        now_ts = time.time()
        signals = []
        
        # Stage 1: volatility pre-filter (v6: 0.8%→0.5%)
        def check_vol(sym):
            try:
                k15 = fetch_klines(sym, "15m", 3)
                if k15 and len(k15) >= 2:
                    p0 = float(k15[0]["c"]); pn = float(k15[-1]["c"])
                    chg = abs((pn-p0)/p0*100) if p0 > 0 else 0
                    if chg > 0.5: return (sym, chg)
            except: pass
            return None
        
        candidates = []
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(check_vol, s): s for s in get_dynamic_coins()}
            for f in as_completed(futures, timeout=60):
                r = f.result()
                if r: candidates.append(r)
        
        candidates.sort(key=lambda x: -x[1])
        candidates = candidates[:12]
        
        if candidates:
            def full_scan(sym_chg):
                sym, chg = sym_chg
                try:
                    k5 = fetch_klines(sym, "5m", 100)
                    k15 = fetch_klines(sym, "15m", 30)
                    k1 = fetch_klines(sym, "1h", 30)
                    fr = fetch_funding_rate(sym)
                    price = fetch_price(sym)
                    if not k5 or len(k5) < 20: return None
                    
                    # Orderbook imbalance
                    ob_imb = fetch_orderbook_imbalance(sym, 100)
                    
                    # VOTE
                    vote_dir, vote_count, vr_list, vs_list = yaobi_vote(k5, k15, k1, fr, ob_imb)
                    if not vote_dir: return None
                    
                    # Price gatekeeper
                    passed, gate_msg = price_gatekeeper(vote_dir, k5)
                    if not passed: return None
                    
                    # === v9: penalty locks (deduct score, not hard block) ===
                    cv5 = calc_cvd(k5, 3)
                    penalty = 0
                    # lock1: CVD reverse penalty -8
                    if vote_dir == "long" and cv5 < -25:
                        penalty += 8
                    if vote_dir == "short" and cv5 > 25:
                        penalty += 8
                    # lock2: weak volume penalty -5
                    vols = [float(k["v"]) for k in k5[-20:]]
                    avg_v = sum(vols[:-1]) / max(len(vols)-1, 1)
                    if vols[-1] < avg_v * 0.5:
                        penalty += 5
                    # v11: 15m CVD must confirm 5m direction
                    if k15 and len(k15) >= 6:
                        cv15 = calc_cvd(k15, 3)
                        if vote_dir == "long" and cv15 < -10:
                            penalty += 8
                        if vote_dir == "short" and cv15 > 10:
                            penalty += 8
                    # lock3: 4H trend oppose penalty -6
                    if k1 and len(k1) >= 20:
                        from hermes_core import detect_structure
                        s4, _ = detect_structure(k1)
                        if vote_dir == "long" and s4 == "down":
                            penalty += 6
                        if vote_dir == "short" and s4 == "up":
                            penalty += 6
                    # Abort only if total penalty >= 12
                    if penalty >= 12:
                        return None
                    
                    # === v6: Cooldown check ===
                    ckey = "%s_%s" % (sym, vote_dir)
                    last_push = _cooldowns.get(ckey, 0)
                    if now_ts - last_push < 600:  # 10 minute cooldown same direction
                        return None  # skip, will catch on next scan
                    
                    # === v6: Flip detection ===
                    old_dir = _last_dir.get(sym)
                    is_flip = old_dir and old_dir != vote_dir and old_dir in ("long","short")
                    _last_dir[sym] = vote_dir
                    
                    # === v6: Persistence ===
                    skey = "%s_%s" % (sym, vote_dir)
                    if old_dir == vote_dir:
                        _streaks[skey] = _streaks.get(skey, 1) + 1
                    else:
                        _streaks[skey] = 1
                        # Clear opposite streak
                        op_key = "%s_%s" % (sym, ("short" if vote_dir=="long" else "long"))
                        _streaks.pop(op_key, None)
                    
                    streak = _streaks.get(skey, 1)
                    
                    # v10: weighted scoring + flip bonus + persistent penalty + exhaustion check
                    score = int(vote_count * 8) - penalty
                    # v10: flip bonus (catching reversals early)
                    if is_flip:
                        score += 3
                    # v10: persistent penalty (trend tail risk, streak>=3)
                    if streak >= 3:
                        score -= 4
                    # v12: exhaustion gate - >3% move in signal direction = no chase
                    if vote_dir == "long" and chg > 3:
                        return None
                    if vote_dir == "short" and chg < -3:
                        return None
                    
                    # BUGFIX v9: reasons set BEFORE mercu extend (was being overwritten)
                    reasons = vr_list if vote_dir == "long" else vs_list
                    
                    # === v7: MerCu cross-validation ===
                    m = validate_signal(sym, vote_dir)
                    if m:
                        score += m["bonus"]
                        if m["flags"]:
                            reasons.extend(m["flags"])
                        if m["warnings"]:
                            for w in m["warnings"]:
                                reasons.append("MERU:" + w[:30])
                    
                    # v13: OB final gate - if OB>30% opposes final signal, flip it
                    ob_val = ob_imb.get("imbalance", 0) if ob_imb else 0
                    if vote_dir == "long" and ob_val < -30:
                        vote_dir = "short"
                        reasons.insert(0, "OB_flip_short(%d%%)" % int(abs(ob_val)))
                        score -= 5
                    elif vote_dir == "short" and ob_val > 30:
                        vote_dir = "long"
                        reasons.insert(0, "OB_flip_long(%d%%)" % int(ob_val))
                        score -= 5
                    
                    # v14: minimum signal quality gate - need >=3 independent confirmations
                    confirmations = 0
                    # 1. 5m CVD same direction (>15%)
                    cv5_check = calc_cvd(k5, 3)
                    if (vote_dir == "long" and cv5_check > 15) or (vote_dir == "short" and cv5_check < -15):
                        confirmations += 1
                    # 2. 15m CVD same direction (>10%)
                    if k15 and len(k15) >= 6:
                        cv15_check = calc_cvd(k15, 3)
                        if (vote_dir == "long" and cv15_check > 10) or (vote_dir == "short" and cv15_check < -10):
                            confirmations += 1
                    # 3. OB same direction (>20%)
                    ob_val = ob_imb.get("imbalance", 0) if ob_imb else 0
                    if (vote_dir == "long" and ob_val > 20) or (vote_dir == "short" and ob_val < -20):
                        confirmations += 1
                    # 4. Mercu confirms (bonus > 0)
                    if m and m["bonus"] > 0:
                        confirmations += 1
                    # 5. Volume burst confirms
                    if len(k5) >= 6:
                        vr = sum(float(k5[i]["v"]) for i in range(-3, 0))
                        vp = max(sum(float(k5[i]["v"]) for i in range(-6, -3)), 0.001)
                        if vr / vp > 1.5:
                            confirmations += 1
                    
                    if confirmations < 3:
                        return None
                    
                    return {
                        "sym": sym, "price": price, "dir": vote_dir,
                        "score": score, "reasons": reasons,
                        "chg": round(chg, 1), "source": "VOTE",
                        "is_flip": is_flip, "streak": streak,
                        "ob_imb": ob_imb.get("imbalance", 0) if ob_imb else 0,
                        "mercu": {"confirmed": m["confirmed"], "bonus": m["bonus"],
                                  "oi": m["mercu_oi"], "flow": m["mercu_flow"],
                                  "retail": m["mercu_retail"]} if m else {}
                    }
                except Exception as e:
                    return None
            
            with ThreadPoolExecutor(max_workers=4) as ex:
                futures2 = {ex.submit(full_scan, c): c for c in candidates}
                for f in as_completed(futures2, timeout=180):
                    r = f.result()
                    # v8: Adaptive threshold based on Fear & Greed
                    adaptive_min = 20
                    if fng is not None:
                        if fng < 20: adaptive_min = 14  # ????: ????, ???
                        elif fng > 75: adaptive_min = 26  # ????: ????, ???
                    if r and r["score"] >= adaptive_min:
                        signals.append(r)
                        # Mark cooldown
                        _cooldowns["%s_%s" % (r["sym"], r["dir"])] = now_ts
        
        # v11: choppy market detection
        if signals:
            has_long = any(s["dir"] == "long" for s in signals)
            has_short = any(s["dir"] == "short" for s in signals)
            if has_long and has_short:
                signals = [s for s in signals if s["score"] >= adaptive_min + 8]
        # Push
        if signals:
            signals.sort(key=lambda x: -x["score"])
            t = datetime.now(BJT).strftime("%m/%d %H:%M")
            lines = ["----------------", "  🎯 妖币扫描 V12 | %s" % t, "----------------"]
            
            longs = [s for s in signals if s["dir"] == "long"]
            shorts = [s for s in signals if s["dir"] == "short"]
            
            if longs:
                lines.append("  🟢 ━━ 做多信号 ━━")
                for s in longs[:5]:
                    sym = s["sym"].replace("USDT", "")
                    reason_str = " | ".join(s.get("reasons", [])[:3])
                    badges = ""
                    if s.get("is_flip"): badges += "🚨翻转 "
                    if s.get("streak", 1) >= 3: badges += "🔥持久"
                    ob = s.get("ob_imb", 0)
                    ob_str = " OB:%+d%%" % int(ob) if abs(ob) > 10 else ""
                    cross_badge = get_badge(sym, "long", "yaobi")
                    lines.append("    做多 %-6s %3d分 $%s %s%s%s" % (sym, s["score"], s["price"], badges, cross_badge, ob_str))
                    if reason_str:
                        lines.append("      → %s" % reason_str[:70])
            
            if shorts:
                lines.append("  🔴 ━━ 做空信号 ━━")
                for s in shorts[:5]:
                    sym = s["sym"].replace("USDT", "")
                    reason_str = " | ".join(s.get("reasons", [])[:3])
                    badges = ""
                    if s.get("is_flip"): badges += "🚨翻转 "
                    if s.get("streak", 1) >= 3: badges += "🔥持久"
                    ob = s.get("ob_imb", 0)
                    ob_str = " OB:%+d%%" % int(ob) if abs(ob) > 10 else ""
                    cross_badge = get_badge(sym, "short", "yaobi")
                    lines.append("    做空 %-6s %3d分 $%s %s%s%s" % (sym, s["score"], s["price"], badges, cross_badge, ob_str))
                    if reason_str:
                        lines.append("      → %s" % reason_str[:70])
            
            lines.append("----------------")
            cross_sigs = [{"sym": s["sym"].replace("USDT",""), "dir": s["dir"]} for s in signals]
            write_signals("yaobi", cross_sigs)
            feishu_app_send(chr(10).join(lines), chat_id=CHAT_ID)
            print("[YaobiV14] pushed %d (L:%d S:%d) in %.1fs" % (len(signals), len(longs), len(shorts), time.time()-t0))
        else:
            print("[YaobiV14] no signals in %.1fs" % (time.time()-t0))
        
        elapsed = time.time() - t0
        time.sleep(max(10, 120 - elapsed))
    except Exception as e:
        print("[YaobiV14] error:", e)
        import traceback
        traceback.print_exc()
        time.sleep(30)