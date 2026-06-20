#!/usr/bin/env python3
"""Fix pipeline_tracker.py: auto-generate pid, dedup, limit size"""

path = "/home/ubuntu/hermes-v2/services/pipeline_tracker.py"
with open(path) as f:
    content = f.read()

# Fix 1: In signal_confirmed, generate pid if None + check dedup
old_sig = '''def signal_confirmed(pid, symbol, direction, score, price, source, indicators=None):
    '''Record signal confirmation (Èë³¡). Links to early pipeline if exists.'''
    d = _load()
    
    # Find or create pipeline
    if pid not in d['active']:'''

new_sig = '''def signal_confirmed(pid, symbol, direction, score, price, source, indicators=None):
    """Record signal confirmation. Auto-generates pid if None. Deduplicates by symbol+direction."""
    d = _load()
    
    # Auto-generate pid if None
    if pid is None:
        pid = '%s_%s_%d' % (symbol.replace('USDT',''), direction, int(time.time()/120)*120)
    
    # Check dedup: if same symbol+direction exists in active, update instead of create
    for existing_pid, existing_pipe in list(d['active'].items()):
        if existing_pipe.get('symbol') == symbol.replace('USDT','') and existing_pipe.get('direction') == direction:
            # Update existing pipe
            pipe = existing_pipe
            pipe['status'] = 'active'
            if not pipe.get('signal_time'):
                pipe['signal_time'] = time.time()
                pipe['signal_time_str'] = datetime.now(BJT).strftime('%m/%d %H:%M:%S')
                pipe['signal_price'] = price
                pipe['signal_score'] = score
                pipe['signal_source'] = source
                pipe['signal_indicators'] = indicators or {}
            _save(d)
            return pid
    
    # Find or create pipeline
    if pid not in d['active']:'''

content = content.replace(old_sig, new_sig)

# Fix 2: Limit total pipelines to 500
old_limit = "    if len(d['pipelines']) > 1000:\n        d['pipelines'] = d['pipelines'][-1000:]"
new_limit = "    if len(d['pipelines']) > 500:\n        d['pipelines'] = d['pipelines'][-500:]"
content = content.replace(old_limit, new_limit)

# Fix 3: In take_snapshots, add max_active limit
old_snap_loop = "    for pid, pipe in list(d['active'].items()):\n        if pipe.get('settled'):\n            continue"
new_snap_loop = "    for pid, pipe in list(d['active'].items())[:50]:  # Cap at 50 active\n        if pipe.get('settled'):\n            continue"
content = content.replace(old_snap_loop, new_snap_loop)

with open(path, 'w') as f:
    f.write(content)
print("pipeline_tracker.py fixed")
