import subprocess

path = "/app/app/services/hermes_strategies/__init__.py"
result = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "cat", path], capture_output=True, text=True)
content = result.stdout

# Find the broken section and fix it
old_broken = """        _pc = {"count": 0, "errors": 0, "empty_streak": 0}
runner._running = True
        poll_thread = threading.Thread(target=mercu_poll_loop, daemon=True, name="mercu-poll")
        poll_thread.start()"""

new_fixed = """        _pc = {"count": 0, "errors": 0, "empty_streak": 0}
        
        runner._running = True
        poll_thread = threading.Thread(target=mercu_poll_loop, daemon=True, name="mercu-poll")
        poll_thread.start()
        watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True, name="mercu-watchdog")
        watchdog_thread.start()"""

if old_broken in content:
    content = content.replace(old_broken, new_fixed)
    print("Fixed indentation")
else:
    print("Broken section not found exactly, checking...")
    # Try to find _pc line
    idx = content.find('_pc = {')
    if idx > 0:
        print(f"Found _pc at {idx}:")
        print(content[idx:idx+200])
    exit(1)

with open("/tmp/init_v3_fixed.py", "w", encoding="utf-8") as f:
    f.write(content)

result = subprocess.run(["sudo", "docker", "cp", "/tmp/init_v3_fixed.py", f"hermes-backend:{path}"], capture_output=True, text=True)
print(f"cp: {result.returncode}")

# Verify syntax
result2 = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "python3", "-c", 
    "import py_compile; py_compile.compile('/app/app/services/hermes_strategies/__init__.py', doraise=True); print('SYNTAX OK')"], 
    capture_output=True, text=True)
print(result2.stdout)
print(result2.stderr)
