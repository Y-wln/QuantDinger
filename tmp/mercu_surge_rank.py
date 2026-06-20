#!/usr/bin/env python3
"""mercu_surge_rank.py v1 - Surge acceleration + Rank hot coins + AI briefs"""
import sys, os, json, time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/home/ubuntu/scripts/agents")
from hermes_core import feishu_app_send, fetch_price
from signal_tracker import track_signals

BJT = timezone(timedelta(hours=8))
DATA = "/home/ubuntu/scripts/agents/mercu_data"
CHAT_MONITOR = "oc_ab05adb5111c8ae30d5816ec66f79897"
CHAT_YAOBI = "oc_58c90b36ddb0d64439c64ed83a16b47b"

_seen = {}
_pushed_briefs = set()
_pushed_surge = {}

def load(name, ttl=180):
    p = os.path.join(DATA, name)
    if not os.path.exists(p): return None
    if time.time() - os.path.getmtime(p) > ttl: return None
    with open(p) as f: return json.load(f)

def should_push(key, cooldown=600):
    now = time.time()
    if now - _seen.get(key, 0) < cooldown:
        return False
    _seen[key] = now
    return True

print("[MerCu Surge+Rank] starting...")
feishu_app_send("MerCu Surge+Rank+AI Briefs | " + datetime.now(BJT).strftime("%H:%M"), chat_id=CHAT_MONITOR)

while True:
    try:
        t0 = time.time()
        signals = []
        
        # ===== 1. SURGE - Acceleration signals (閹绘劕澧犳０鍕劅) =====
        surge = load("surge.json", ttl=120)
        if surge:
            surge_signals = []
            for item in surge.get("items", []):
                sym = str(item.get("sym", "")).upper()
                accel = float(item.get("accel", 0))
                total = int(item.get("total", 0))
                rhythm = item.get("rhythm", "")
                direction = item.get("dir", "up")
                
                # Only alert on NEW accelerating coins
                key = "surge_" + sym
                prev_accel = _pushed_surge.get(sym, 0)
                _pushed_surge[sym] = accel
                
                # Trigger: accel > 1.5 OR first time appearing with accel > 1.0
                if accel >= 1.5 or (accel >= 1.0 and prev_accel == 0):
                    if not should_push(key, 900):
                        continue
                    
                    d = "long" if direction == "up" else "short"
                    score = min(int(accel * 20), 60)
                    
                    if rhythm == "閺嬩線鈧喎鍟嬫径?:
                        score += 15
                        tag = "NEW"
                    elif rhythm == "閸旂娀鈧喎鍟嬫径?:
                        score += 10
                        tag = "ACCEL"
                    elif rhythm == "閹镐胶鐢绘姗€顣?:
                        score += 5
                        tag = "HOT"
                    else:
                        tag = ""
                    
                    reasons = ["Surge:x%.1f" % accel, rhythm]
                    
                    try:
                        price = fetch_price(sym + "USDT")
                    except:
                        price = 0
                    
                    surge_signals.append({
                        "sym": sym, "dir": d, "score": score, "price": price or 0,
                        "reasons": reasons, "tag": tag, "accel": accel
                    })
            
            if surge_signals:
                surge_signals.sort(key=lambda x: -x["score"])
                surge_signals = surge_signals[:5]
                
                t = datetime.now(BJT).strftime("%m/%d %H:%M")
                lines = ["----------------", "  Surge | %s" % t, "----------------"]
                lines.append("  Surge (" + str(surge.get("window","1h")) + ")")
                
                for s in surge_signals:
                    emoji = "" if s["dir"] == "long" else ""
                    tag_str = (" " + s["tag"]) if s["tag"] else ""
                    price_str = (" $%.4f" % s["price"]) if s["price"] > 0 else ""
                    lines.append("    %s %s %dpt%s%s" % (emoji, s["sym"], s["score"], tag_str, price_str))
                    lines.append("      %s" % " | ".join(s["reasons"]))
                
                lines.append("----------------")
                feishu_app_send(chr(10).join(lines), chat_id=CHAT_YAOBI)
                
                # Track
                tracker_sigs = [{"sym": s["sym"], "dir": s["dir"], "price": s["price"], "score": s["score"], "reasons": s["reasons"]} for s in surge_signals]
                track_signals(tracker_sigs, source="surge")
                signals.extend(surge_signals)
                print("[Surge] %d signals" % len(surge_signals))
        
        # ===== 2. RANK - Hot coin analysis =====
        rank = load("rank.json", ttl=300)
        if rank:
            top_coins = rank.get("top", [])[:5]
            if top_coins:
                rank_signals = []
                for item in top_coins:
                    sym = str(item.get("sym", "")).replace("$", "").upper()
                    rank_num = item.get("rank", 0)
                    count = item.get("count", 0)
                    direction = item.get("dir", "up")
                    dir_pct = item.get("dirPct", "")
                    tags = item.get("tags", [])
                    ai = (item.get("ai") or "")[:100]
                    
                    # Map to signal direction
                    d = "long" if direction == "up" else "short"
                    score = 10 + min(count // 10, 40)
                    
                    # Bonus for clear direction
                    if dir_pct == "100%":
                        score += 10
                    
                    reasons = ["Rank#%d(%d)" % (rank_num, count)]
                    if tags:
                        reasons.append(",".join(tags))
                    
                    key = "rank_" + sym
                    if should_push(key, 1800):
                        try:
                            price = fetch_price(sym + "USDT")
                        except:
                            price = 0
                        
                        rank_signals.append({
                            "sym": sym, "dir": d, "score": score, "price": price or 0,
                            "reasons": reasons, "ai": ai
                        })
                
                if rank_signals:
                    # Push rank summary periodically
                    t = datetime.now(BJT).strftime("%m/%d %H:%M")
                    lines = ["----------------", "  Rank 24h | %s" % t, "----------------"]
                    
                    for s in rank_signals:
                        dir_label = "+" if s["dir"] == "long" else "-"
                        price_str = (" $%.4f" % s["price"]) if s["price"] > 0 else ""
                        lines.append("  #%d %s %s %dpt%s" % (
                            rank_signals.index(s) + 1,
                            s["sym"],
                            dir_label,
                            s["score"],
                            price_str
                        ))
                        lines.append("    %s" % " | ".join(s["reasons"]))
                        if s.get("ai"):
                            lines.append("    AI: %s" % s["ai"][:80])
                    
                    lines.append("----------------")
                    feishu_app_send(chr(10).join(lines), chat_id=CHAT_MONITOR)
                    print("[Rank] %d coins" % len(rank_signals))
        
        # ===== 3. AI BRIEFS =====
        briefs = load("briefs.json", ttl=600)
        if briefs:
            for brief in briefs.get("briefs", []):
                bid = brief.get("module", "") + brief.get("title", "")
                if bid not in _pushed_briefs:
                    _pushed_briefs.add(bid)
                    # Keep only last 20
                    if len(_pushed_briefs) > 50:
                        _pushed_briefs = set(list(_pushed_briefs)[-30:])
                    
                    t = datetime.now(BJT).strftime("%m/%d %H:%M")
                    lines = ["----------------", "  AI | %s | %s" % (brief.get("title",""), t), "----------------"]
                    lines.append(brief.get("headline", ""))
                    for b in brief.get("bullets", [])[:4]:
                        label = b.get("label", "")
                        text = b.get("text", "")
                        if label:
                            lines.append("  [%s] %s" % (label, text[:80]))
                        else:
                            lines.append("  %s" % text[:80])
                    lines.append("----------------")
                    feishu_app_send(chr(10).join(lines), chat_id=CHAT_MONITOR)
                    print("[Briefs] %s" % brief.get("title", ""))
        
        elapsed = time.time() - t0
        print("[MerCuSR] cycle %.1fs | surge:%d rank:%d" % (
            elapsed,
            len(signals),
            len(rank.get("top",[])) if rank else 0
        ))
        time.sleep(max(10, 60 - elapsed))
        
    except Exception as e:
        print("[MerCuSR] error:", e)
        import traceback; traceback.print_exc()
        time.sleep(30)