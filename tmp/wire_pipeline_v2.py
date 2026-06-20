"""Wire pipeline_tracker into agent_orchestrator.py - v2 careful"""
import re

with open('/home/ubuntu/scripts/agents/agent_orchestrator.py') as f:
    lines = f.readlines()

# 1. Add import after the last existing import line
for i, line in enumerate(lines):
    if 'from signal_tracker import track' in line and i < 20:
        lines.insert(i + 1, 'from pipeline_tracker import stage_raw, stage_confirm, stage_filter, stage_scored, stage_opened, stage_decision\n')
        break

# 2. Add signal_id + stage_raw after score extraction
for i, line in enumerate(lines):
    if line.strip().startswith("score = sig['score']") and 'skip_reason' in lines[i+1] if i+1 < len(lines) else False:
        indent = line[:len(line) - len(line.lstrip())]
        lines.insert(i + 1, f'{indent}signal_id = str(int(time.time() * 1000000)) + "_" + sym\n')
        lines.insert(i + 2, f'{indent}stage_raw(signal_id, sig)\n')
        break

# 3. After leading_confirm call, add stage_confirm
for i, line in enumerate(lines):
    if 'sig = self.leading_confirm(sig, sig.get("regime", "trending"))' in line:
        indent = line[:len(line) - len(line.lstrip())]
        lines.insert(i + 1, f'{indent}stage_confirm(signal_id, sig)\n')
        break

# 4. After held check
for i, line in enumerate(lines):
    if "skip_reason = 'held'; sig['_skip_reason'] = 'held'" in line:
        indent = line[:len(line) - len(line.lstrip())]
        # Insert AFTER the continue
        if i+1 < len(lines) and 'continue' in lines[i+1]:
            lines.insert(i+1, f'{indent}stage_filter(signal_id, False, "held", {{"held": True}})\n')
            lines.insert(i+2, f'{indent}stage_decision(signal_id, "held")\n')
        break

# 5. After max_pos check
for i, line in enumerate(lines):
    if "skip_reason = 'max_pos'; sig['_skip_reason'] = 'max_pos'" in line:
        indent = line[:len(line) - len(line.lstrip())]
        if i+1 < len(lines) and 'continue' in lines[i+1]:
            lines.insert(i+1, f'{indent}stage_filter(signal_id, False, "max_pos", {{"max_pos": True}})\n')
            lines.insert(i+2, f'{indent}stage_decision(signal_id, "max_pos")\n')
        break

# 6. After cvd_weak
for i, line in enumerate(lines):
    if "sig['_skip_reason'] = 'cvd_weak(" in line:
        indent = line[:len(line) - len(line.lstrip())]
        if i+1 < len(lines) and 'continue' in lines[i+1]:
            lines.insert(i+1, f'{indent}stage_filter(signal_id, False, "cvd_weak", {{"cvd": cvd}})\n')
            lines.insert(i+2, f'{indent}stage_decision(signal_id, "cvd_weak")\n')
        break

# 7. After btc_block
for i, line in enumerate(lines):
    if "skip_reason = 'btc_block_' + direction" in line:
        indent = line[:len(line) - len(line.lstrip())]
        # Find the continue after this block
        for j in range(i, min(i+5, len(lines))):
            if 'continue' in lines[j]:
                lines.insert(j, f'{indent}stage_filter(signal_id, False, skip_reason, {{"btc_blocked": True}})\n')
                lines.insert(j+1, f'{indent}stage_decision(signal_id, skip_reason)\n')
                break
        break

# 8. After fast_votes_low
for i, line in enumerate(lines):
    if 'sig["_skip_reason"] = "fast_votes_low"' in line or "sig['_skip_reason'] = 'fast_votes_low'" in line:
        indent = line[:len(line) - len(line.lstrip())]
        if i+1 < len(lines) and 'continue' in lines[i+1]:
            lines.insert(i+1, f'{indent}stage_filter(signal_id, False, "fast_votes_low", {{"votes": sig.get("fast_votes",0)}})\n')
            lines.insert(i+2, f'{indent}stage_decision(signal_id, "fast_votes_low")\n')
        break

# 9. Add stage_scored before Smart Money section
for i, line in enumerate(lines):
    if 'Smart money (Binance top trader ratio)' in line:
        indent = line[:len(line) - len(line.lstrip())]
        scored_block = [
            f'{indent}# Pipeline: record final score with all adjustments\n',
            f'{indent}indicator_scores = {{}}\n',
            f'{indent}for k, v in sig.get("details", {{}}).items():\n',
            f'{indent}    if isinstance(v, str) and v.startswith(("+", "-")):\n',
            f'{indent}        try:\n',
            f'{indent}            indicator_scores[k] = int(v.split()[0])\n',
            f'{indent}        except:\n',
            f'{indent}            indicator_scores[k] = v\n',
            f'{indent}adj = []\n',
            f'{indent}if sig.get("leading_bonus",0): adj.append("leading_bonus+"+str(sig.get("leading_bonus",0)))\n',
            f'{indent}if lb != 0: adj.append("quick_launch+"+str(lb))\n',
            f'{indent}if jin10_bonus != 0: adj.append("jin10+"+str(jin10_bonus))\n',
            f'{indent}stage_scored(signal_id, score, adj, indicator_scores)\n',
            f'{indent}\n',
        ]
        for j, sl in enumerate(scored_block):
            lines.insert(i + j, sl)
        break

with open('/home/ubuntu/scripts/agents/agent_orchestrator.py', 'w') as f:
    f.writelines(lines)

print('Pipeline tracker wired v2 - checking syntax...')
