import sys
sys.path.insert(0, "/home/ubuntu/scripts/agents")
sys.dont_write_bytecode = True

# Import directly from the fixed file
import importlib.util
spec = importlib.util.spec_from_file_location("yaobi_v8", "/home/ubuntu/scripts/yaobi_v8.py")
yaobi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(yaobi)

# Test analyze_one
r = yaobi.analyze_one("OPGUSDT")
print(f"OPGUSDT result: {r}")

# Also test a few others
for sym in ["SAHARAUSDT", "STRAXUSDT", "TAOUSDT", "ALLOUSDT"]:
    r2 = yaobi.analyze_one(sym)
    if r2:
        print(f"{sym}: score={r2['score']} sig={r2['signal']}")
    else:
        print(f"{sym}: None (no signal)")
