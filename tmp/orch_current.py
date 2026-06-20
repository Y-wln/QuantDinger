# -*- coding: utf-8 -*-
import sys, os, time, json, threading, traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, '/home/ubuntu/scripts/agents')
from hermes_core import (feishu_send, load_state, save_state, should_alert,
    fetch_orderbook_imbalance, fetch_1m_cvd, fetch_tape_pressure,
    fetch_price, fetch_klines, atr, fetch_taker_volume, fetch_long_short_ratio,
    fetch_funding_rate, fetch_oi_history, fetch_fear_greed, calc_cvd, ema, rsi, adx, detect_structure)
from kline_cache import cached_fetch
from liq_ws import get_liq_magnet_score, liq_data, liq_lock, save_cache

COINS = ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT',
    'DOGEUSDT','LINKUSDT','AVAXUSDT','DOTUSDT','LTCUSDT','INJUSDT',
    'APTUSDT','FETUSDT','AAVEUSDT','TRUMPUSDT','DASHUSDT','ZECUSDT','WLDUSDT','HYPEUSDT']
# v43: backtest-positive coins only for auto-trading (all coins still scanned for signal push)
MAJOR_COINS = ["BTCUSDT", "ETHUSDT"]
TRADE_COINS = ['DOGEUSDT','ADAUSDT','BTCUSDT','BNBUSDT','AVAXUSDT','INJUSDT','SOLUSDT','XRPUSDT','ETHUSDT','FETUSDT','TRUMPUSDT']
SCAN_INTERVAL = 60
MAX_WORKERS = 5
MAX_POSITIONS = 3
SIGNAL_THRESHOLD = 25

class Orchestrator:
    def __init__(self):
        self.running = False
        self.signal_cooldowns = {}
        self._4h_klines = {}
        self._last_4h_fetch = 0
        self.market = None
        self.technical = None
        self.sentiment = None
        self.position = None

    def _init_agents(self):
        from agent_technical import TechnicalAgent
        from agent_position import PositionAgent
        self.technical = TechnicalAgent()
        self.position = PositionAgent()
        self.position.max_positions = MAX_POSITIONS

    def _scan_one(self, sym):
        try:
            if time.time() - self._last_4h_fetch > 3600 or sym not in self._4h_klines:
                k4 = fetch_klines(sym, '4h', 300)
                if len(k4) >= 50: self._4h_klines[sym] = k4
            else:
                k4 = self._4h_klines.get(sym, [])
            k1 = fetch_klines(sym, '1h', 300); k5 = fetch_klines(sym, '5m', 50); k15 = fetch_klines(sym, '15m', 30)
            price = fetch_price(sym)
            if len(k4) < 50 or len(k1) < 50 or price <= 0:
                return None
            fr = fetch_funding_rate(sym)
            result = self.technical.analyze(k4, k1, k5, k15, sym, funding_rate=fr)
            result['symbol'] = sym; result['price'] = price; result['atr_val'] = atr(k4)
            result['cvd1h'] = result.get('details', {}).get('cvd1h', 0)
            return result
        except Exception as e:
            return None

    def scan_all(self):
        self._last_4h_fetch = time.time()
        signals = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(self._scan_one, sym): sym for sym in COINS}
            for f in as_completed(futures):
                r = f.result()
                if r and r.get('signal') != 'wait':
                    signals.append(r)
        # Jin10 macro + news context (v45.5: fixed scope)
        try:
            from jin10_client import macro_score, news_score
            ms, mreasons = macro_score()
            ns, headlines = news_score()
            jin10_bonus = 0
            if ms != 0:
                jin10_bonus += ms
            if abs(ns) >= 6:
                jin10_bonus += ns // 2
            for s in signals:
                s['jin10'] = {'macro': ms, 'news': ns, 'headlines': headlines[:3]}
        except Exception:
            pass
        return signals

    def _scan_one_quick(self, sym):
        try:
            k4 = self._4h_klines.get(sym)
            if not k4 or len(k4) < 50:
                k4 = fetch_klines(sym, '4h', 300)
                if len(k4) >= 50: self._4h_klines[sym] = k4
            k1 = fetch_klines(sym, '1h', 300); k5 = fetch_klines(sym, '5m', 50); k15 = fetch_klines(sym, '15m', 30)
            price = fetch_price(sym)
            if len(k4) >= 50 and len(k1) >= 50 and price > 0:
                fr = fetch_funding_rate(sym)
                r = self.technical.analyze(k4, k1, k5, k15, sym, funding_rate=fr)
                r['symbol'] = sym; r['price'] = price; r['atr_val'] = atr(k4)
                r['cvd1h'] = r.get('details', {}).get('cvd1h', 0)
                return r
        except Exception:
            pass
        return None

    def scan_quick(self):
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(self._scan_one_quick, sym): sym for sym in COINS}
            for f in as_completed(futures):
                r = f.result()
                if r and r.get('signal') != 'wait':
                    results.append(r)
        return results


    def leading_confirm(self, sig, regime="trending"):
        """v7: 快指标3票门控 - 1mCVD+orderbook+tape必须>=2票同意才放行
        慢指标(OI/费率/LSR/FnG)保留为加分项"""
        sym = sig["symbol"]
        direction = sig["signal"]
        score = sig["score"]
        bonus = 0
        reasons = []
        fast_votes = 0  # 快指标投票
        fast_reasons = []

        # ====== 快指标门控 (实时, 低延迟) ======
        # 1m CVD
        try:
            cvd1m = fetch_1m_cvd(sym)
            sig["cvd1m"] = cvd1m
            if direction == "long" and cvd1m > 7:
                fast_votes += 1; fast_reasons.append("1mCVD:" + str(int(cvd1m)) + "%")
            elif direction == "short" and cvd1m < -7:
                fast_votes += 1; fast_reasons.append("1mCVD:" + str(int(cvd1m)) + "%")
            elif (direction == "long" and cvd1m < -8) or (direction == "short" and cvd1m > 8):
                fast_votes -= 1; reasons.append("1mCVD反向-1票")
        except Exception:
            pass

        # Orderbook
        try:
            ob = fetch_orderbook_imbalance(sym)
            if ob:
                imb = ob.get("imbalance", 0)
                sig["orderbook"] = imb
                if direction == "long" and imb > 3:
                    fast_votes += 1; fast_reasons.append("盘口偏买:" + str(int(imb)) + "%")
                elif direction == "short" and imb < -3:
                    fast_votes += 1; fast_reasons.append("盘口偏卖:" + str(int(imb)) + "%")
                elif (direction == "long" and imb < -8) or (direction == "short" and imb > 8):
                    fast_votes -= 1; reasons.append("盘口反向-1票")
        except Exception:
            pass

        # Tape
        try:
            tape = fetch_tape_pressure(sym)
            if tape:
                sig["tape"] = tape.get("pressure", "neutral")
                lp = tape.get("large_net", 0)
                if direction == "long" and tape["pressure"] == "bullish":
                    fast_votes += 1; fast_reasons.append("tape偏买")
                    if lp >= 3: bonus += 6; reasons.append("大单买入+6")
                elif direction == "short" and tape["pressure"] == "bearish":
                    fast_votes += 1; fast_reasons.append("tape偏卖")
                    if lp <= -3: bonus += 6; reasons.append("大单卖出+6")
                elif (direction == "long" and tape["pressure"] == "bearish") or                      (direction == "short" and tape["pressure"] == "bullish"):
                    fast_votes -= 1; reasons.append("tape反向-1票")
        except Exception:
            pass

        # ====== 慢指标加分 (不参与门控) ======
        # OI四象限
        try:
            oi_hist = fetch_oi_history(sym, "5m", 5)
            if oi_hist and len(oi_hist) >= 4:
                oi_change = (oi_hist[-1] - oi_hist[0]) / oi_hist[0] * 100 if oi_hist[0] > 0 else 0
                price_change = 0
                k1 = fetch_klines(sym, "1h", 50)
                if k1 and len(k1) >= 2:
                    price_change = (k1[-1]["c"] - k1[0]["c"]) / k1[0]["c"] * 100
                if oi_change > 2 and abs(price_change) <= 0.5:
                    label = "主力吸筹"; oi_score = 15
                elif oi_change > 2 and price_change > 0.5:
                    label = "多头建仓"; oi_score = 10 if direction == "long" else -5
                elif oi_change > 2 and price_change < -0.5:
                    label = "空头建仓"; oi_score = 10 if direction == "short" else -5
                elif oi_change < -2 and abs(price_change) <= 0.5:
                    label = "主力出货"; oi_score = -15
                elif oi_change < -2 and price_change > 0.5:
                    label = "多头撤退"; oi_score = -8
                elif oi_change < -2 and price_change < -0.5:
                    label = "空头撤退"; oi_score = 8 if direction == "long" else 0
                else:
                    label = "OI平稳"; oi_score = 0
                # v45: regime-based OI weight
                oi_score_raw = oi_score
                if regime == "trending":
                    oi_score = int(oi_score * 1.7)
                elif regime == "ranging":
                    oi_score = int(oi_score * 0.5)
                bonus += oi_score
                reasons.append("OI:" + label + "(" + str(round(oi_change,1)) + "%)" + (" +" if oi_score>0 else " ") + str(oi_score))
                sig["oi"] = {"change": round(oi_change,1), "label": label, "score": oi_score}
        except Exception:
            pass

        # Taker
        try:
            taker = fetch_taker_volume(sym)
            if direction == "long" and taker.get("trend") == "bullish":
                bonus += 8; reasons.append("主动买盘+8")
            elif direction == "short" and taker.get("trend") == "bearish":
                bonus += 8; reasons.append("主动卖盘+8")
            elif (direction == "long" and taker.get("trend") == "bearish") or                  (direction == "short" and taker.get("trend") == "bullish"):
                bonus -= 10; reasons.append("主动盘反向-10")
            sig["taker"] = taker.get("ratio", 0.5)
        except Exception:
            pass

        # LSR
        try:
            lsr = fetch_long_short_ratio(sym)
            if direction == "long" and lsr < 0.8:
                bonus += 5; reasons.append("散户看空(反向+5)")
            elif direction == "short" and lsr > 2.5:
                bonus += 5; reasons.append("散户看多(反向+5)")
            elif (direction == "long" and lsr > 2.5) or (direction == "short" and lsr < 0.8):
                bonus -= 8; reasons.append("散户同向拥挤-8")
            sig["lsr"] = round(lsr, 2)
        except Exception:
            pass

        # Funding
        try:
            fr = fetch_funding_rate(sym)
            if direction == "long" and fr < -0.001:
                bonus += 8; reasons.append("费率极负(逼空+8)")
            elif direction == "short" and fr > 0.003:
                bonus += 8; reasons.append("费率极正(逼多+8)")
            elif (direction == "long" and fr > 0.003) or (direction == "short" and fr < -0.001):
                bonus -= 5; reasons.append("费率不利-5")
            sig["funding"] = round(fr*100, 4)
        except Exception:
            pass

        # FnG
        try:
            fng = getattr(self, "_cached_fng", None)
            if fng is None or time.time() - getattr(self, "_cached_fng_ts", 0) > 120:
                fng = fetch_fear_greed()
                self._cached_fng = fng
                self._cached_fng_ts = time.time()
            # v45.7: FnG context-aware - only penalize counter-trend
            trend_4h = sig.get("details", {}).get("struct4", "")
            trend_is_up = trend_4h and "+" in str(trend_4h)
            trend_is_down = trend_4h and "-" in str(trend_4h)
            if fng <= 20 and direction == "long":
                bonus += 8; reasons.append("极度恐惧(反向+8)")
            elif fng >= 80 and direction == "short":
                bonus += 8; reasons.append("极度贪婪(反向+8)")
            elif fng <= 20 and direction == "short" and trend_is_up:
                bonus -= 10; reasons.append("恐慌逆势做空-10")
            elif fng >= 80 and direction == "long" and trend_is_down:
                bonus -= 10; reasons.append("贪婪逆势做多-10")
            sig["fng"] = fng
        except Exception:
            pass

        # ====== 门控结果 ======
        sig["fast_votes"] = fast_votes
        sig["fast_reasons"] = fast_reasons
        sig["leading_bonus"] = bonus
        sig["leading_reasons"] = reasons + fast_reasons

        # v45: 3-vote gate
        if fast_votes >= 3:
            sig["confirmed"] = True
            sig["confidence"] = "high"
        elif fast_votes >= 2 and abs(score) >= SIGNAL_THRESHOLD:
            sig["confirmed"] = True
            sig["confidence"] = "medium"
        elif fast_votes == 1 and abs(score) >= 35:
            sig["confirmed"] = True
            sig["confidence"] = "low"
        else:
            sig["confirmed"] = False
            sig["confidence"] = "none"
            sig["_skip_reason"] = f"fast_votes={fast_votes} score={abs(score):.0f} (need 3 or 2+TH)"

        return sig

    def lightning_check(self, sig):
        """v45.4: vol 3x + tape = instant entry"""
        sym = sig["symbol"]
        direction = sig["signal"]
        try:
            from hermes_core import fetch_klines
            k1m = fetch_klines(sym, "1m", 30)
            if not k1m or len(k1m) < 20:
                return False
            vols = [float(k["v"]) for k in k1m[-20:]]
            avg_vol = sum(vols[:-1]) / max(len(vols) - 1, 1)
            cur_vol = vols[-1]
            if cur_vol < avg_vol * 3.0:
                return False
            tape_val = sig.get("tape", "neutral")
            if tape_val == "neutral":
                from hermes_core import fetch_tape_pressure
                tp = fetch_tape_pressure(sym)
                if tp:
                    tape_val = tp.get("pressure", "neutral")
            if direction == "long" and tape_val != "bullish":
                return False
            if direction == "short" and tape_val != "bearish":
                return False
            vol_ratio = cur_vol / avg_vol if avg_vol > 0 else 0
            sig["lightning"] = True
            sig["lightning_details"] = "vol:" + str(round(vol_ratio, 1)) + "x tape:" + str(tape_val)
            return True
        except Exception:
            return False
    def btc_vane(self, sym=None):
        try:
            k4 = self._4h_klines.get("BTCUSDT", [])
            if not k4 or len(k4) < 50:
                k4 = fetch_klines("BTCUSDT", "4h", 100)
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
                    # ????????????????
                    return (trend, True, True)  # allow both, score filter in process_signals
                else:
                    # ??/?????BTC??
                    return (trend, True, True)
            return (trend, trend != "down", trend != "up")
        except Exception:
            return ("unknown", True, True)

    def monitor_positions(self):
        try:
            pos = self.position.get_positions()
            for sym in list(pos.keys()):
                price = fetch_price(sym)
                if price <= 0: continue
                p = pos[sym]
                entry = p['entry_price']
                direction = p['direction']
                if direction == 'long':
                    pp = (price-entry)/entry*100
                    if pp > 3:
                        ns = price*0.985
                        if ns > p['sl']: p['sl'] = round(ns,4)
                    if pp > 6:
                        ns = price*0.992
                        if ns > p['sl']: p['sl'] = round(ns,4)
                else:
                    pp = (entry-price)/entry*100
                    if pp > 3:
                        ns = price*1.015
                        if ns < p['sl']: p['sl'] = round(ns,4)
                    if pp > 6:
                        ns = price*1.008
                        if ns < p['sl']: p['sl'] = round(ns,4)
                # Live PnL update
                p['pnl_pct'] = round(pp, 2)
                p['pnl'] = round(pp, 2)
                if direction == 'long':
                    if price > p.get('highest', entry):
                        p['highest'] = round(price, 4)
                else:
                    if price < p.get('lowest', entry):
                        p['lowest'] = round(price, 4)
                # ????
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
                elif (direction=='long' and price<=p['sl']) or (direction=='short' and price>=p['sl']):
                    ok, msg, result = self.position.close_position(sym, price, '止损')
                    if ok and len(result) > 2:
                        self.position.notify_close(sym, ('close','',result[2]))
                        print('['+time.strftime('%H:%M:%S')+'] CLOSE '+sym+' SL PnL:'+str(round(result[2].get('pnl_pct',0),2))+'%')
                elif (direction=='long' and price>=p['tp']) or (direction=='short' and price<=p['tp']):
                    ok, msg, result = self.position.close_position(sym, price, '止盈')
                    if ok and len(result) > 2:
                        self.position.notify_close(sym, ('close','',result[2]))
                        print('['+time.strftime('%H:%M:%S')+'] CLOSE '+sym+' TP PnL:'+str(round(result[2].get('pnl_pct',0),2))+'%')
            save_state(self.position.state)
        except Exception:
            pass

    def process_signals(self, signals):
        self._dag_count = 0  # v46: reset DAG counter per cycle
        """v43: 级联仓位 + 白名单过滤 + 全程领先确认 + CVD背离"""
        signals = [s for s in signals if s.get("symbol","") in TRADE_COINS]
        if not signals: return
        btc_trend, _, _ = self.btc_vane()
        dir_cn = '空' if btc_trend == 'down' else ('多' if btc_trend == 'up' else '?')
        print("[" + time.strftime("%H:%M:%S") + "] BTC风向:" + dir_cn)
        signals.sort(key=lambda x: abs(x['score']), reverse=True)
        for sig in signals:
            try:
                sym = sig['symbol']
                direction = sig['signal']
                fast_sig = sig.get('fast_signal', 'wait')
                # 快轨优先: 领先指标信号优先于标准轨
                if fast_sig != 'wait':
                    if direction == 'wait' or direction != fast_sig:
                        direction = fast_sig
                        sig['_fast_entry'] = True
                        print(f'  ⚡快轨入场 {sym} dir={fast_sig} fast_score={sig.get("fast_score",0)}')
                score = sig['score']
                skip_reason = None; sig['_skip_reason'] = None; tier2_restricted = False
                price = sig['price']
                cvd = sig.get('cvd1h', 0)
                atr_val = sig.get('atr_val', 0)

                # Run leading_confirm FIRST so tracking always has trigger data
                sig = self.leading_confirm(sig, sig.get("regime", "trending"))
                
                if self.position.has_position(sym):
                    skip_reason = 'held'; sig['_skip_reason'] = 'held'
                    continue
                if len(self.position.get_positions()) >= MAX_POSITIONS:
                    skip_reason = 'max_pos'; sig['_skip_reason'] = 'max_pos'
                    continue
                ck = sym + '_' + direction
                if ck in self.signal_cooldowns:
                    if time.time() - self.signal_cooldowns[ck] < 600:
                        skip_reason = 'cooldown'; sig['_skip_reason'] = 'cooldown'
                abs_score = abs(score)
                if abs(cvd) < 5 and abs_score < 35:
                    sig['_skip_reason'] = 'cvd_weak(' + str(int(cvd)) + ')'
                    continue
                _, allow_long, allow_short = self.btc_vane(sym)
                # BTC风向放松: 极度恐贪(FnG<=15或>=85)或高分(>=30)可逆势
                btc_blocked = False
                if direction == 'long' and not allow_long:
                    btc_blocked = True
                if direction == 'short' and not allow_short:
                    btc_blocked = True
                if btc_blocked:
                    try:
                        fng_now = fetch_fear_greed()
                    except:
                        fng_now = 50
                    if fng_now <= 15 and direction == 'long':
                        pass
                    elif fng_now >= 85 and direction == 'short':
                        pass
                    elif abs_score >= 40:
                        # v45: counter-trend penalty
                        score = int(score * 0.7)
                        sig["score"] = score
                        sig["_btc_penalty"] = True
                    else:
                        skip_reason = 'btc_block_' + direction
                        sig['_skip_reason'] = 'btc_block_' + direction
                        continue

                # Check leading_confirm result (already computed above)
                if not sig.get("confirmed", False):
                    if not sig.get("_skip_reason"):
                        sig["_skip_reason"] = "fast_votes_low"
                    continue
                lead_bonus = sig.get("leading_bonus", 0)
                fast_votes = sig.get("fast_votes", 0)
                score += lead_bonus
                abs_score = abs(score)
                if fast_votes >= 2 and abs_score >= SIGNAL_THRESHOLD - 5:
                    abs_score = max(abs_score, SIGNAL_THRESHOLD)

                # ====== 3m+5m快速启动 ======
                lb, lr = self.quick_launch_bonus(sym, direction)
                if lb != 0:
                    score += lb
                    existing = sig.get('leading_reasons', [])
                    existing.extend(lr)
                    sig['leading_reasons'] = existing
                    abs_score = abs(score)

                # v45: lightning check
                if self.lightning_check(sig):
                    sig["_lightning"] = True
                    print("  LIGHTNING " + sym + " " + direction + " " + sig.get("lightning_details", ""))

                li = sig.get('leading_reasons', [])
                if li:
                    print('  leading ' + sym + ': ' + ','.join(li[:4]) + ' final=' + str(score))

                # v45.5: Jin10 macro sentiment
                jin10_data = sig.get('jin10', {})
                jin10_bonus = jin10_data.get('macro', 0) + jin10_data.get('news', 0) // 2
                if jin10_bonus != 0:
                    score += jin10_bonus
                    abs_score = abs(score)
                    sig['score'] = score

                # v46.1: Smart money (Binance top trader ratio)
                try:
                    from smart_money import smart_money_score
                    sm = smart_money_score(sym)
                    if sm and sm.get("direction") != "neutral":
                        sm_score = sm["score"]
                        if (direction == "long" and sm_score > 0) or (direction == "short" and sm_score < 0):
                            score += abs(sm_score) // 2
                            sig.setdefault("extras", {})["smart_money"] = sm["label"]
                            abs_score = abs(score)
                            sig["score"] = score
                except:
                    pass

                # ====== v46: DAG多节点确认 (仅top2信号,避免超时) ======
                if not hasattr(self, '_dag_count'):
                    self._dag_count = 0
                if self._dag_count < 2:
                    self._dag_count += 1
                    try:
                        from hermes_dag import dag as dag_instance
                        dag_result = dag_instance.run(sym, fast=True)
                        if dag_result and dag_result.get("signal") != "wait":
                            dag_signal = dag_result["signal"]
                            dag_breakdown = dag_result.get("breakdown", {})
                            dag_agree = sum(1 for v in dag_breakdown.values() if (direction == "long" and v > 0) or (direction == "short" and v < 0))
                            dag_disagree = sum(1 for v in dag_breakdown.values() if (direction == "long" and v < 0) or (direction == "short" and v > 0))
                            sig["dag_confirm"] = True
                            sig["dag_agree"] = dag_agree
                            sig["dag_total"] = dag_agree + dag_disagree
                            sig["dag_signal"] = dag_signal
                            sig["dag_score"] = dag_result.get("score", 0)
                            if dag_signal != direction:
                                score = score * 0.6
                                abs_score = abs(score)
                                sig["dag_conflict"] = True
                                print("  DAG冲突 " + sym + ": analyze=" + direction + " dag=" + dag_signal + " score=" + str(int(score)))
                            elif dag_agree >= 3:
                                score += 5
                                abs_score = abs(score)
                                sig["dag_bonus"] = 5
                                print("  DAG确认 " + sym + ": " + str(dag_agree) + "/" + str(dag_agree+dag_disagree) + " nodes agree")
                    except Exception as e:
                        print("  DAG skip " + sym + ": " + str(e)[:50])

                # ====== v46: Congress辩论(仅在快慢指标冲突时触发) ======
                fast = sig.get("fast_score", 0)
                if fast != 0 and ((fast > 0 and score < 0) or (fast < 0 and score > 0)):
                    # 快慢指标方向冲突 → AI辩论裁决
                    try:
                        from congress_debate import bull_bear_debate
                        node_data = {
                            "trend": {"score": -8 if struct4 == "down" else (8 if struct4 == "up" else 0), "signals": [f"4h {struct4}", f"1h {struct1}", f"MACD {macd}"]},
                            "momentum": {"score": rsi_bonus if "rsi_bonus" in dir() else 0, "signals": [f"RSI {rsi1h}"]},
                            "volume": {"score": cv4 + cv1_fast if "cv4" in dir() else 0, "signals": [f"CVD accel {cv_accel}"]},
                            "sentiment": {"score": fng_score if "fng_score" in dir() else 0, "signals": [f"FnG {fng}"]},
                            "liquidity": {"score": 0, "signals": ["N/A"]},
                        }
                        debate = bull_bear_debate(sym, price, fng, node_data, rounds=1)
                        if debate:
                            sig["congress"] = debate.get("verdict", "")[:150]
                            sig["congress_dir"] = debate.get("node_dir", "")
                            print("  Congress " + sym + ": " + debate.get("node_dir", "?") + "(" + str(debate.get("node_total",0)) + ")")
                    except Exception as e:
                        print("  Congress skip: " + str(e)[:50])

                
                # ====== CVD背离检测 ======
                div = self._cvd_price_divergence(sym, direction, price, cvd)
                if div:
                    score += div['bonus']
                    abs_score = abs(score)
                    sig['leading_reasons'] = sig.get('leading_reasons', []) + [div['label']]
                    print('  CVD背离 ' + sym + ': ' + div['label'])

                # v45.5: HVN/LVN volume profile support/resistance
                try:
                    from hermes_core import volume_profile_zones
                    k15_for_vp = fetch_klines(sym, '15m', 100)
                    if k15_for_vp and len(k15_for_vp) >= 30:
                        vp = volume_profile_zones(k15_for_vp, bins=8)
                        if vp and vp.get('hvns'):
                            for hvn_price in vp['hvns']:
                                if direction == 'long' and abs(price - hvn_price) / price < 0.02:
                                    score += 5
                                    sig.setdefault('leading_reasons', []).append(f'HVN支撑(hvn_price)')
                                    break
                                elif direction == 'short' and abs(price - hvn_price) / price < 0.02:
                                    score += 5
                                    sig.setdefault('leading_reasons', []).append(f'HVN压力(hvn_price)')
                                    break
                except Exception:
                    pass
                
                # ====== v44.8 双模式: 趋势 vs 震荡 ======
                is_trend = False
                try:
                    k4_for_mode = self._4h_klines.get('BTCUSDT', [])
                    if not k4_for_mode or len(k4_for_mode) < 30:
                        k4_for_mode = fetch_klines('BTCUSDT', '4h', 50)
                    if len(k4_for_mode) >= 30:
                        adv_val = adx(k4_for_mode)
                        struct4, _ = detect_structure(k4_for_mode)
                        k1_for_mode = fetch_klines('BTCUSDT', '1h', 50)
                        struct1, _ = detect_structure(k1_for_mode) if k1_for_mode and len(k1_for_mode)>=30 else ('neutral',0)
                        is_trend = (adv_val > 30 and struct4 == struct1 and struct4 != 'neutral')
                except Exception: pass

                # ====== 级联仓位 v2 ======
                # 全仓仅给>40分, 避免重仓踩雷
                cascade_level = 2; cascade_pct = 0.60
                if tier2_restricted:
                    cascade_level = 1; cascade_pct = 0.25
                elif abs_score >= 50:   cascade_level = 3; cascade_pct = 0.04
                elif abs_score >= 35:   cascade_level = 2; cascade_pct = 0.04
                elif abs_score >= 25:   cascade_level = 1; cascade_pct = 0.04
                if fast_votes >= 3 and cascade_level == 0 and abs_score >= 25:
                    cascade_level = 1; cascade_pct = 0.20

                print(f'  >> {sym} {direction} final_score={score} abs={abs_score} cvd={cvd} lvl={cascade_level}')
                # === 市场状态 ===
                regime = sig.get('regime', 'trending')
                
                # v45: 震荡市降低评分敏感度
                if regime == "ranging":
                    score = int(score * 0.8)
                    abs_score = abs(score)
                    sig["score"] = score
                # === 震荡市场: RSI极值过滤 ===
                if regime == 'ranging' and abs_score < 30:
                    rs = sig.get('rsi_val', 50)
                    if direction == 'long' and rs > 35:
                        sig['_skip_reason'] = 'range_rsi_high'
                        continue
                    if direction == 'short' and rs < 65:
                        sig['_skip_reason'] = 'range_rsi_low'
                        continue
                
                # === v44.4: 清算磁吸加成 ===
                liq_mag = get_liq_magnet_score(sym, price)
                if liq_mag and liq_mag.get('score', 0) != 0:
                    liq_score = liq_mag['score']
                    score += liq_score
                    abs_score = abs(score)
                    if liq_score > 0:
                        sig.setdefault('leading_reasons', []).append(f'liq_mag+{liq_score}')
                    else:
                        sig.setdefault('leading_reasons', []).append(f'liq_mag{liq_score}')

                if abs_score >= SIGNAL_THRESHOLD:
                    print(f'  !!! TRADE {sym} {direction} score={score} cascade={cascade_level} !!!')
                    self.signal_cooldowns[ck] = time.time()
                    try:
                        import json as _json
                        with open('/home/ubuntu/scripts/agents/per_coin_params.json') as _f:
                            pcp = _json.load(_f)
                        if sym in pcp:
                            sl_pct = pcp[sym]['sl_pct']
                            tp_pct = pcp[sym]['tp_pct']
                        elif atr_val > 0 and price > 0:
                            ap = atr_val/price
                            sl_pct = max(0.04, min(0.10, ap*2))
                            tp_pct = max(0.08, min(0.20, ap*4))
                        else:
                            sl_pct = 0.04; tp_pct = 0.08
                    # v44.8: trend mode wider TP
                    except Exception:
                        sl_pct = 0.04; tp_pct = 0.08
                    # v44.8: trend mode wider TP
                    if is_trend:
                        tp_pct = sl_pct * 5.0
                    # === 自适应: 震荡市放宽止损,趋势市紧止损 ===
                    if regime == 'ranging':
                        sl_pct = max(sl_pct, 0.05)  # 震荡最小SL=5%
                        tp_pct = min(tp_pct, 0.03)  # 震荡最大TP=3%
                        if cascade_level >= 2:
                            cascade_level = 2  # 震荡不重仓
                    # v44.1: all positions fixed 4%, no SL widening
                    # === v44.7: 动态进场 ===
                    # RSI filter: 不追高(>65) 不追低(<35)
                    try:
                        k1_for_rsi = self._4h_klines.get(sym, [])
                        if not k1_for_rsi:
                            k1_for_rsi = fetch_klines(sym, '1h', 50)
                        c_arr = [k['c'] for k in k1_for_rsi[-30:]] if k1_for_rsi else []
                        rs_val = rsi(c_arr, 14) if len(c_arr) >= 14 else 50
                        if isinstance(rs_val, list): rs_val = rs_val[-1] if rs_val else 50
                        if direction == 'long' and rs_val > 65:
                            sig['_skip_reason'] = 'rsi_overbought(' + str(int(rs_val)) + ')'
                            print(f'  RSI skip {sym}: {int(rs_val)} overbought')
                            continue
                        if direction == 'short' and rs_val < 35:
                            sig['_skip_reason'] = 'rsi_oversold(' + str(int(rs_val)) + ')'
                            print(f'  RSI skip {sym}: {int(rs_val)} oversold')
                            continue
                    except Exception: pass

                    # Pullback entry: long=min(price, EMA20), short=max(price, EMA20)
                    opt_price = price
                    try:
                        k1_for_ema = self._4h_klines.get(sym, [])
                        if not k1_for_ema:
                            k1_for_ema = fetch_klines(sym, '1h', 50)
                        e_arr = ema([k['c'] for k in k1_for_ema[-30:]], 20) if k1_for_ema else []
                        e20 = e_arr[-1] if e_arr else price
                        if direction == 'long' and e20 < price:
                            opt_price = e20
                        elif direction == 'short' and e20 > price:
                            opt_price = e20
                        if abs(opt_price-price)/price > 0.0001:
                            print(f'  entry_opt {sym}: {price}->{opt_price}')
                            price = opt_price
                            sl_pct_adj = sl_pct
                            sl = price*(1-sl_pct_adj) if direction=='long' else price*(1+sl_pct_adj)
                            tp = price*(1+tp_pct) if direction=='long' else price*(1-tp_pct)
                    except Exception: pass

                    # Generate track_id for linking to outcome
                    tid = None
                    try:
                        from signal_tracker import track
                        tid = track(sym.replace('USDT',''), direction, score, price, 'orch',
                              extras={'decision': 'pending_open'})
                    except:
                        pass

                    ok, msg = self.position.open_position(
                        sym, direction, price, score, cvd, sl_pct, tp_pct,
                        cascade=cascade_level, size_pct=cascade_pct, track_id=tid)
                    if ok:
                        r = sig.get('leading_reasons', [])
                        lvl_tag = ['1试仓', '2加仓', '3全仓'][cascade_level-1]
                        print('['+time.strftime('%H:%M:%S')+'] '+lvl_tag+' '+sym+' '+direction+
                              ' s='+str(score)+' SL='+str(round(sl_pct*100,1))+'% TP='+str(round(tp_pct*100,1))+'%')
                        self.position.notify_open(sym, direction, price, score, cvd,
                            r[:4], cascade=cascade_level)

            except Exception as e:
                pass
        # Summary of filtered signals
        # ====== Pipeline tracking: record every signal's complete journey ======
        for s in signals:
            try:
                from signal_tracker import track
                sym_clean = s['symbol'].replace('USDT', '')
                direction = s.get('signal', s.get('direction', '?'))
                score = s.get('score', 0)
                price = s.get('price', 0)
                details = s.get('details', {})
                skip = s.get('_skip_reason')
                confirmed = s.get('confirmed', False)
                
                # Decision: what happened to this signal?
                if skip:
                    decision = skip
                elif confirmed:
                    decision = 'open'
                elif s.get('_fast_entry'):
                    decision = 'fast_entry'
                else:
                    decision = 'no_decision'
                
                indicator_scores = {}
                for k, v in details.items():
                    if isinstance(v, str) and v.startswith(('+', '-')):
                        try:
                            indicator_scores[k] = int(v.split()[0])
                        except:
                            indicator_scores[k] = v
                
                track(sym_clean, direction, score, price, 'orch',
                      extras={
                          'trend_4h': details.get('struct4', '?'),
                          'trend_1h': details.get('struct1', '?'),
                          'indicators': indicator_scores,
                          'triggers': s.get('leading_reasons', [])[:5],
                          'fast_votes': s.get('fast_votes', 0),
                          'cvd1h': s.get('cvd1h', 0),
                          'confirmed': confirmed,
                          'decision': decision,
                      })
            except:
                pass

        filtered = [s for s in signals if s.get('_skip_reason')]
        if filtered:
            parts = []
            for s in filtered[:5]:
                parts.append(s['symbol'].replace('USDT','') + ':' + s.get('_skip_reason','?'))
            print('  filtered: ' + ','.join(parts))

    def quick_launch_bonus(self, sym, direction):
        """3m+5m CVD 快速启动检测"""
        try:
            from hermes_core import fetch_klines
            k3 = fetch_klines(sym, '3m', 5)
            k5 = fetch_klines(sym, '5m', 5)
            if len(k3) < 3 or len(k5) < 3:
                return 0, []
            c3 = float(k3[-1][4]) if k3[-1][4] else 0
            o3 = float(k3[-1][1]) if k3[-1][1] else 1
            c5 = float(k5[-1][4]) if k5[-1][4] else 0
            o5 = float(k5[-1][1]) if k5[-1][1] else 1
            price_dir_3m = 1 if c3 > o3 else (-1 if c3 < o3 else 0)
            price_dir_5m = 1 if c5 > o5 else (-1 if c5 < o5 else 0)
            vol3_list = [float(k[5]) for k in k3[-3:]]
            vol5_list = [float(k[5]) for k in k5[-3:]]
            buy3 = sum(vol3_list[i] for i in range(min(3, len(k3))) if i < len(k3) and float(k3[-(i+1)][4]) > float(k3[-(i+1)][1]))
            buy5 = sum(vol5_list[i] for i in range(min(3, len(k5))) if i < len(k5) and float(k5[-(i+1)][4]) > float(k5[-(i+1)][1]))
            total3 = sum(vol3_list) or 1
            total5 = sum(vol5_list) or 1
            buy_ratio_3m = buy3 / total3
            buy_ratio_5m = buy5 / total5
            bonus = 0
            reasons = []
            if direction == 'long' and price_dir_3m == 1 and price_dir_5m == 1:
                bonus += 5; reasons.append('3m+5m同步上涨+5')
            elif direction == 'short' and price_dir_3m == -1 and price_dir_5m == -1:
                bonus += 5; reasons.append('3m+5m同步下跌+5')
            if direction == 'long' and buy_ratio_3m > 0.6:
                bonus += 4; reasons.append('3m买量占比高+4')
            elif direction == 'short' and buy_ratio_3m < 0.4:
                bonus += 4; reasons.append('3m卖量占比高+4')
            avg5 = sum(vol5_list) / len(vol5_list) if vol5_list else 1
            last_vol = vol5_list[-1] if vol5_list else 0
            if last_vol > avg5 * 1.5:
                bonus += 3; reasons.append('5m放量1.5x+3')
            return bonus, reasons
        except Exception:
            return 0, []

    def _cvd_price_divergence(self, sym, direction, price, cvd_1h):
        """CVD价格背离: 价涨CVD卖=诱多, 价跌CVD买=吸筹"""
        try:
            from hermes_core import fetch_klines
            k15 = fetch_klines(sym, '15m', 8)
            if len(k15) < 6:
                return None
            p0, pn = float(k15[0][4]), float(k15[-1][4])
            price_chg = (pn - p0) / p0 * 100 if p0 > 0 else 0
            # 背离判断
            if direction == 'long' and cvd_1h < -10 and price_chg > 0.3:
                return {'bonus': 8, 'label': '价涨CVD卖=诱空陷阱+8'}
            if direction == 'short' and cvd_1h > 10 and price_chg < -0.3:
                return {'bonus': 8, 'label': '价跌CVD买=诱多陷阱+8'}
            if direction == 'long' and cvd_1h > 15 and price_chg < -0.2:
                return {'bonus': 6, 'label': '跌+CVD买=吸筹反弹+6'}
            if direction == 'short' and cvd_1h < -15 and price_chg > 0.2:
                return {'bonus': 6, 'label': '涨+CVD卖=派发出货+6'}
            return None
        except Exception:
            return None




    def run(self):
        self._init_agents()
        self.running = True
        loop = 0
        print('['+time.strftime('%H:%M:%S')+'] v46.6 short-balance+synergy+gate+flash+yaobi+dag starting...')
        feishu_send('Hermes v45.11 | trade-only | '+datetime.now().strftime('%H:%M'))
        while self.running:
            try:
                loop += 1
                t0 = time.time()
                if loop==1 or time.time()-self._last_4h_fetch>3600:
                    signals = self.scan_all(); label='full'
                else:
                    signals = self.scan_quick(); label='quick'
                t1 = time.time()
                print('['+time.strftime('%H:%M:%S')+'] Loop#'+str(loop)+' '+label+' '+str(round(t1-t0,1))+'s, signals:'+str(len(signals)))
                if signals: self.process_signals(signals)
                self.monitor_positions()
                # Push methods moved to standalone services (yb/sig/rev/flash)
                # orch now focused on scan + trade + monitor only
                time.sleep(max(1, SCAN_INTERVAL-(time.time()-t0)))
            except KeyboardInterrupt: break
            except Exception as e:
                print('Loop error: '+str(e)); traceback.print_exc(); time.sleep(10)
        self.running = False

if __name__ == '__main__':
    Orchestrator().run()
