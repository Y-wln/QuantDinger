import base64
script = """#!/bin/bash
if [ -z "$1" ]; then
    python3
else
    echo "$1" | base64 -d | python3
fi
"""
with open("/tmp/s_script", "w") as f:
    f.write(script)
