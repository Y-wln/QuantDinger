import os
script = """#!/bin/bash
if [ -z "$1" ]; then
    python3
else
    echo "$1" | base64 -d | python3
fi
"""
# Use \n for newlines, ensure Unix line endings
with open("C:/Users/ZhuanZ/Documents/Codex/2026-06-06/hermes-agent-agent-agent/tmp/mks.py", "w", newline="\n") as f:
    f.write(f'''import os
script = {repr(script)}
with open("/tmp/s_final", "w") as f:
    f.write(script)
print("wrote")
''')
