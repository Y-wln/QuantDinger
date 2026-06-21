import subprocess

path = "/app/app/services/selfcheck.py"
result = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "cat", path], capture_output=True, text=True)
content = result.stdout

old_block = """        # 2. Strategy service check
        try:
            from app.services.hermes_strategy_service import get_hermes_strategy_service
            svc = get_hermes_strategy_service()
            results["strategy"] = {
                "status": "OK" if svc._running else "STOPPED",
                "positions": len(svc.positions),
                "detail": f"Running={svc._running}, positions={len(svc.positions)}"
            }
        except Exception as e:
            results["strategy"] = {"status": "ERROR", "detail": str(e)[:100]}"""

new_block = """        # 2. Strategy check (Hermes V3)
        try:
            from app.services.hermes_strategies import get_hermes_v3_status
            v3 = get_hermes_v3_status()
            if v3.get("status") == "not_started":
                results["strategy"] = {
                    "status": "STOPPED",
                    "positions": 0,
                    "detail": "V3 not started"
                }
            elif v3.get("status") == "error":
                results["strategy"] = {
                    "status": "ERROR",
                    "positions": 0,
                    "detail": v3.get("error", "unknown")[:100]
                }
            else:
                pos = v3.get("positions", {})
                pos_count = len(pos) if isinstance(pos, dict) else 0
                results["strategy"] = {
                    "status": "OK",
                    "positions": pos_count,
                    "detail": f"V3 running, subs={v3.get(\"event_bus_subscribers\",0)}"
                }
        except Exception as e:
            results["strategy"] = {"status": "ERROR", "detail": str(e)[:100]}"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("Replaced strategy check -> V3")
else:
    print("Old block NOT found!")
    idx = content.find("Strategy service check")
    if idx > 0:
        print(content[idx:idx+400])
    exit(1)

# Also fix the exchange check - line should be around "4. Exchange check"
# Let me check exchange section
idx_ex = content.find("Exchange check")
if idx_ex > 0:
    print(f"\nExchange check at {idx_ex}:")
    print(content[idx_ex:idx_ex+500])

with open("/tmp/selfcheck_new.py", "w", encoding="utf-8") as f:
    f.write(content)

result = subprocess.run(["sudo", "docker", "cp", "/tmp/selfcheck_new.py", f"hermes-backend:{path}"], capture_output=True, text=True)
print(f"\ncp: {result.returncode}")

# Verify
result2 = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "python3", "-c",
    "import py_compile; py_compile.compile('/app/app/services/selfcheck.py', doraise=True); print('SYNTAX OK')"],
    capture_output=True, text=True)
print(result2.stdout)
print(result2.stderr)
