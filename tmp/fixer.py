import base64

with open(r'C:\Users\ZhuanZ\Documents\Codex\2026-06-06\hermes-agent-agent-agent\tmp\mercu_lab\run.py', 'rb') as f:
    text = f.read().decode('utf-8')

# Fix 1: _scored_ids indent
text = text.replace('         self._scored_ids = set()', '        self._scored_ids = set()')

# Fix 2: broken dedup block
old = 'if label is None:\n             return None\n             eid = sym + \"_\" + dim + \"_\" + str(a.get(\"first_seen_ts\",0))\n             if eid in self._scored_ids:\n                 return None\n             self._scored_ids.add(eid)\n        \n            return None'
new = 'if label is None:\n            return None\n\n        # Dedup: skip already-scored anomalies\n        eid = f\"{sym}_{dim}_{a.get(chr(39)+chr(39)+chr(39)+'first_seen_ts'+chr(39)+chr(39)+chr(39)+', 0)}\"\n        if eid in self._scored_ids:\n            return None\n        self._scored_ids.add(eid)'

text = text.replace(old, new)

with open(r'C:\Users\ZhuanZ\Documents\Codex\2026-06-06\hermes-agent-agent-agent\tmp\mercu_lab\run.py', 'wb') as f:
    f.write(text.encode('utf-8'))

b64 = base64.b64encode(text.encode('utf-8')).decode()
with open(r'C:\Users\ZhuanZ\Documents\Codex\2026-06-06\hermes-agent-agent-agent\tmp\mercu_lab\run.b64', 'w') as f:
    f.write(b64)
print(f'OK {len(text)} bytes')
