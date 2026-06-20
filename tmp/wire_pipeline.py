"""Wire pipeline_tracker into agent_orchestrator.py"""
import re

with open('/home/ubuntu/scripts/agents/agent_orchestrator.py') as f:
    code = f.read()

# 1. Add import
old_import = "from signal_tracker import track"
new_import = "from signal_tracker import track\nfrom pipeline_tracker import stage_raw, stage_confirm, stage_filter, stage_scored, stage_opened, stage_decision"
code = code.replace(old_import, new_import)

# 2. After getting sym/direction/score, add stage_raw + signal_id
old_raw = """                score = sig['score']
                skip_reason = None; sig['_skip_reason'] = None; tier2_restricted = False"""

new_raw = """                score = sig['score']
                signal_id = str(int(time.time() * 1000000)) + '_' + sym
                stage_raw(signal_id, sig)
                skip_reason = None; sig['_skip_reason'] = None; tier2_restricted = False"""

code = code.replace(old_raw, new_raw)

# 3. After leading_confirm, add stage_confirm
old_confirm = """                # Run leading_confirm FIRST so tracking always has trigger data
                sig = self.leading_confirm(sig, sig.get("regime", "trending"))
                
                if self.position.has_position(sym):"""

new_confirm = """                # Run leading_confirm FIRST so tracking always has trigger data
                sig = self.leading_confirm(sig, sig.get("regime", "trending"))
                stage_confirm(signal_id, sig)
                
                if self.position.has_position(sym):
                    stage_filter(signal_id, False, 'held', {'held': True})"""

code = code.replace(old_confirm, new_confirm)

# 4. After max_pos skip, add stage_filter
old_maxpos = """                if len(self.position.get_positions()) >= MAX_POSITIONS:
                    skip_reason = 'max_pos'; sig['_skip_reason'] = 'max_pos'
                    continue"""

new_maxpos = """                if len(self.position.get_positions()) >= MAX_POSITIONS:
                    skip_reason = 'max_pos'; sig['_skip_reason'] = 'max_pos'
                    stage_filter(signal_id, False, 'max_pos', {'max_pos': True})
                    stage_decision(signal_id, 'max_pos')
                    continue"""

code = code.replace(old_maxpos, new_maxpos)

# 5. After cooldown skip
old_cool = """                if ck in self.signal_cooldowns:
                    if time.time() - self.signal_cooldowns[ck] < 600:
                        skip_reason = 'cooldown'; sig['_skip_reason'] = 'cooldown'"""

new_cool = """                if ck in self.signal_cooldowns:
                    if time.time() - self.signal_cooldowns[ck] < 600:
                        skip_reason = 'cooldown'; sig['_skip_reason'] = 'cooldown'
                        stage_filter(signal_id, False, 'cooldown', {'cooldown': True})
                        stage_decision(signal_id, 'cooldown')"""

code = code.replace(old_cool, new_cool)

# 6. After cvd_weak skip
old_cvd = """                if abs(cvd) < 5 and abs_score < 35:
                    sig['_skip_reason'] = 'cvd_weak(' + str(int(cvd)) + ')'
                    continue"""

new_cvd = """                if abs(cvd) < 5 and abs_score < 35:
                    sig['_skip_reason'] = 'cvd_weak(' + str(int(cvd)) + ')'
                    stage_filter(signal_id, False, 'cvd_weak', {'cvd': cvd, 'abs_score': abs_score})
                    stage_decision(signal_id, 'cvd_weak')
                    continue"""

code = code.replace(old_cvd, new_cvd)

# 7. After btc_block skip
old_btc = """                    else:
                        skip_reason = 'btc_block_' + direction
                        sig['_skip_reason'] = 'btc_block_' + direction
                        continue"""

new_btc = """                    else:
                        skip_reason = 'btc_block_' + direction
                        sig['_skip_reason'] = 'btc_block_' + direction
                        stage_filter(signal_id, False, skip_reason, {'btc_trend': btc_trend})
                        stage_decision(signal_id, skip_reason)
                        continue"""

code = code.replace(old_btc, new_btc, 1)

# 8. After fast_votes_low skip
old_fast = """                if not sig.get("confirmed", False):
                    if not sig.get("_skip_reason"):
                        sig["_skip_reason"] = "fast_votes_low"
                    continue"""

new_fast = """                if not sig.get("confirmed", False):
                    if not sig.get("_skip_reason"):
                        sig["_skip_reason"] = "fast_votes_low"
                    stage_filter(signal_id, False, 'fast_votes_low', {'fast_votes': sig.get('fast_votes', 0)})
                    stage_decision(signal_id, 'fast_votes_low')
                    continue"""

code = code.replace(old_fast, new_fast)

# 9. After all score adjustments, add stage_scored (before position open logic)
# Find the position open logic and add scored before it
old_scored = """                # v46.1: Smart money (Binance top trader ratio)"""

new_scored = """                # Pipeline: record scored stage
                indicator_scores = {}
                for k, v in sig.get('details', {}).items():
                    if isinstance(v, str) and v.startswith(('+', '-')):
                        try:
                            indicator_scores[k] = int(v.split()[0])
                        except:
                            indicator_scores[k] = v
                stage_scored(signal_id, score, 
                    ['leading_bonus+' + str(sig.get('leading_bonus',0)), 
                     'quick_launch+' + str(lb),
                     'jin10+' + str(jin10_bonus)],
                    indicator_scores)
                
                # v46.1: Smart money (Binance top trader ratio)"""

code = code.replace(old_scored, new_scored)

# 10. After position opens, add stage_opened (find open_position call)
old_open = """                    ok, msg = self.position.open_position(
                        sym, direction, price, score, cvd, sl_pct, tp_pct,
                        cascade=cascade_level, size_pct=cascade_pct)"""

new_open = """                    ok, msg = self.position.open_position(
                        sym, direction, price, score, cvd, sl_pct, tp_pct,
                        cascade=cascade_level, size_pct=cascade_pct)
                    if ok:
                        stage_opened(signal_id, price, 
                            price*(1-sl_pct) if direction=='long' else price*(1+sl_pct),
                            price*(1+tp_pct) if direction=='long' else price*(1-tp_pct),
                            cascade_level, cascade_pct)"""

code = code.replace(old_open, new_open)

# Add stage_decision for held signals
old_held = """                if self.position.has_position(sym):
                    skip_reason = 'held'; sig['_skip_reason'] = 'held'
                    continue"""

new_held = """                if self.position.has_position(sym):
                    skip_reason = 'held'; sig['_skip_reason'] = 'held'
                    stage_filter(signal_id, False, 'held', {'held': True})
                    stage_decision(signal_id, 'held')
                    continue"""

# Only apply if the old_held pattern wasn't already replaced
if old_held in code:
    code = code.replace(old_held, new_held)

with open('/home/ubuntu/scripts/agents/agent_orchestrator.py', 'w') as f:
    f.write(code)

print('Pipeline tracker wired into orchestrator')
