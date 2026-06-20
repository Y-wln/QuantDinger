# -*- coding: utf-8 -*-
import sys
p = sys.argv[1] if len(sys.argv) > 1 else '/home/ubuntu/scripts/yaobi_v8.py'
with open(p, encoding='utf-8') as f:
    code = f.read()

# Fix 1: Wrap flash pre-scan in try/except TimeoutError
old = "    # v19: Phase 1 - Flash pre-scan (fast, ~5-8s for 20 coins)\n    t0 = time.time()\n    flash_coins = []\n    with ThreadPoolExecutor(max_workers=12) as ex:\n        ff = {ex.submit(pre_flash, s): s for s, _, _ in candidates[:20]}\n        for f in as_completed(ff, timeout=10):\n            try:\n                ok, d, h = f.result()\n                if ok:\n                    flash_coins.append(ff[f])\n            except: pass\n    t1 = time.time()"

new = "    # v19: Phase 1 - Flash pre-scan (fast, ~5-8s for 20 coins)\n    flash_coins = []\n    try:\n        with ThreadPoolExecutor(max_workers=12) as ex:\n            ff = {ex.submit(pre_flash, s): s for s, _, _ in candidates[:20]}\n            for f in as_completed(ff, timeout=12):\n                try:\n                    ok, d, h = f.result()\n                    if ok:\n                        flash_coins.append(ff[f])\n                except: pass\n    except TimeoutError:\n        pass"

code = code.replace(old, new)

# Fix 2: Add flash log line
old2 = "    scan_order = scan_order[:20]  # limit to 20 for speed\n\n    signals = []"
new2 = "    scan_order = scan_order[:20]\n\n    print(f'[{ts}] flash:{len(flash_coins)} deep:{len(scan_order)} pos:{len(positions)}')\n\n    signals = []"
code = code.replace(old2, new2)

with open(p, 'w', encoding='utf-8') as f:
    f.write(code)

import py_compile
py_compile.compile(p, doraise=True)
print('syntax OK, lines:', len(code.split(chr(10))))
