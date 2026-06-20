#!/bin/bash
echo "=== 1. Directory ==="
cd /home/ubuntu/hermes-v2
find . -name '*.py' -not -path '*/__pycache__/*' -not -path './logs/*' -not -path './data/*' | sort

echo ""
echo "=== 2. Duplicates ==="
for f in $(find . -name '*.py' -not -path '*/__pycache__/*' -exec basename {} \; | sort | uniq -d); do
    echo "DUPLICATE: $f"
    find . -name "$f" -not -path '*/__pycache__/*'
done

echo ""
echo "=== 3. Syntax ==="
errors=0
for f in $(find . -name '*.py' -not -path '*/__pycache__/*' -not -path './logs/*'); do
    python3 -m py_compile "$f" 2>/dev/null || { echo "FAIL: $f"; errors=$((errors+1)); }
done
echo "Errors: $errors"

echo ""
echo "=== 4. Daemon ==="
screen -ls 2>/dev/null | grep v2
ps aux | grep -E 'daemon.py|watchdog.py' | grep -v grep

echo ""
echo "=== 5. Git ==="
git status --short
