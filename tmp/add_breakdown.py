"""Add score breakdown tracking to orchestrator"""
with open("/home/ubuntu/scripts/agents/agent_orchestrator.py") as f:
    code = f.read()

# 1. Init breakdown after score extraction (already done via sed)
# Verify it's there
if '"_score_breakdown"' not in code and "'_score_breakdown'" not in code:
    old = "                score = sig['score']\n                skip_reason"
    new = "                score = sig['score']\n                sig['_score_breakdown'] = {'original': score}\n                skip_reason"
    code = code.replace(old, new, 1)

# 2. Record lead_bonus
old = "                score += lead_bonus"
new = "                score += lead_bonus; sig.setdefault('_score_breakdown',{})['leading_bonus'] = lead_bonus"
code = code.replace(old, new, 1)

# 3. Record quick_launch
old = "                lb, lr = self.quick_launch_bonus(sym, direction)"
new = "                lb, lr = self.quick_launch_bonus(sym, direction); "
code = code.replace(old, new, 1)

old2 = "                if lb != 0:\n                    score += lb"
new2 = "                if lb != 0:\n                    score += lb; sig.setdefault('_score_breakdown',{})['quick_launch'] = lb"
code = code.replace(old2, new2, 1)

# 4. Record jin10
old3 = "                if jin10_bonus != 0:\n                    score += jin10_bonus"
new3 = "                if jin10_bonus != 0:\n                    score += jin10_bonus; sig.setdefault('_score_breakdown',{})['jin10'] = jin10_bonus"
code = code.replace(old3, new3, 1)

# 5. Record smart_money
old4 = "                            score += abs(sm_score) // 2"
new4 = "                            score += abs(sm_score) // 2; sig.setdefault('_score_breakdown',{})['smart_money'] = abs(sm_score)//2"
code = code.replace(old4, new4, 1)

# 6. Record lightning
old5 = "                                score += 5"
new5 = "                                score += 5; sig.setdefault('_score_breakdown',{})['lightning'] = 5"
# Only first occurrence
code = code.replace(old5, new5, 1)

# 7. Add breakdown to pipeline tracking extras
old6 = """                          'cvd1h': s.get('cvd1h', 0),
                          'confirmed': confirmed,
                          'decision': decision,"""
new6 = """                          'cvd1h': s.get('cvd1h', 0),
                          'confirmed': confirmed,
                          'decision': decision,
                          'score_breakdown': s.get('_score_breakdown', {}),
                          'final_score': s.get('score', 0),"""
code = code.replace(old6, new6, 1)

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(code)

print("Score breakdown tracking added")
