import sys
path = '/home/ubuntu/hermes-v2/services/pipeline_tracker.py'
with open(path, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

# Find signal_confirmed start and insert code after 'd = _load()'
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    
    # After "d = _load()" in signal_confirmed, insert pid auto-gen + dedup
    if 'def signal_confirmed' in line:
        # Find the d = _load() line after this
        j = i + 1
        while j < len(lines):
            new_lines.append(lines[j])
            if 'd = _load()' in lines[j]:
                # Insert after this line
                new_lines.append('    if pid is None:\n')
                new_lines.append("        pid = '%s_%s_%d' % (symbol.replace('USDT',''), direction, int(time.time()/120)*120)\n")
                new_lines.append('    for ep, epipe in list(d.get(\"active\",{}).items()):\n')
                new_lines.append('        if epipe.get(\"symbol\") == symbol.replace(\"USDT\",\"\") and epipe.get(\"direction\") == direction:\n')
                new_lines.append('            if not epipe.get(\"signal_time\"):\n')
                new_lines.append('                epipe[\"status\"] = \"active\"\n')
                new_lines.append('                epipe[\"signal_time\"] = time.time()\n')
                new_lines.append('                epipe[\"signal_time_str\"] = datetime.now(BJT).strftime(\"%m/%d %H:%M:%S\")\n')
                new_lines.append('                epipe[\"signal_price\"] = price\n')
                new_lines.append('                epipe[\"signal_score\"] = score\n')
                new_lines.append('                epipe[\"signal_source\"] = source\n')
                new_lines.append('                epipe[\"signal_indicators\"] = indicators or {}\n')
                new_lines.append('            _save(d)\n')
                new_lines.append('            return pid\n')
                i = j + 1
                break
            j += 1
        continue
    
    # Fix limit
    if 'len(d[\\\"pipelines\\\"]) > 1000' in line:
        line = line.replace('1000', '500')
        new_lines[-1] = line
    
    # Fix active cap
    if 'for pid, pipe in list(d[\\\"active\\\"].items()):' in line:
        line = line.replace('list(d[\\\"active\\\"].items()):', 'list(d[\\\"active\\\"].items())[:50]:')
        new_lines[-1] = line
    
    i += 1

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('OK')
