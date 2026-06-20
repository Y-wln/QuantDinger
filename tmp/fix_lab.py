import re

with open("/home/ubuntu/mercu-lab/run.py") as f:
    content = f.read()

# Fix the indentation of _scored_ids
content = content.replace(
    "        self.tracker = tracker\n         self._scored_ids = set()",
    "        self.tracker = tracker\n        self._scored_ids = set()  # dedup"
)

# Fix the dedup logic that got mangled
# Find the score_anomaly method and fix the dedup block
old_block = '''if label is None:
        return None
        eid = sym + "_" + dim + "_" + str(a.get("first_seen_ts",0))
        if eid in self._scored_ids:
        return None
        self._scored_ids.add(eid)'''

new_block = '''if label is None:
            return None

        # Dedup: don't score same anomaly twice
        eid = f"{sym}_{dim}_{a.get('first_seen_ts', 0)}"
        if eid in self._scored_ids:
            return None
        self._scored_ids.add(eid)'''

content = content.replace(old_block, new_block)

with open("/home/ubuntu/mercu-lab/run.py", "w") as f:
    f.write(content)

print("Fixed")
