path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix indentation around line 438-448
old = "                for f in as_completed(futures2, timeout=180):\n                        r = f.result()\n                    # v8: Adaptive threshold"
new = "                for f in as_completed(futures2, timeout=180):\n                    r = f.result()\n                    # v8: Adaptive threshold"
content = content.replace(old, new)

# Also fix the adaptive_min indentation
old2 = "                    adaptive_min = 20\n                    if fng is not None:\n                        if fng < 20: adaptive_min = 14"
new2 = "                    adaptive_min = 20\n                    if fng is not None:\n                        if fng < 20: adaptive_min = 14"
# Actually these should be fine, let me check the whole block

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Indentation fix applied")
