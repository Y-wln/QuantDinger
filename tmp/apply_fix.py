import re
with open("/home/ubuntu/scripts/agents/agent_orchestrator.py") as f:
    code = f.read()

changes = 0

# Fix 1: signal error logging
old1 = "            except Exception as e:\n                pass"
new1 = "            except Exception as e:\n                import traceback; print(f\"  [SIGNAL ERROR] {sym}: {e}\", flush=True); traceback.print_exc()"
if old1 in code:
    code = code.replace(old1, new1)
    changes += 1
    print("FIX1: signal error will now print traceback")
else:
    print("FIX1: pattern not found, checking...")
    if "except Exception as e:" in code and "pass" in code:
        print("  found partial match")

# Fix 2: bare except:pass -> specific exceptions
old2 = "except Exception: pass"
new2 = "except (ValueError, KeyError, TypeError): pass"
count2 = code.count(old2)
code = code.replace(old2, new2)
changes += count2
print(f"FIX2: {count2} bare except:pass -> specific exceptions")

with open("/home/ubuntu/scripts/agents/agent_orchestrator.py", "w") as f:
    f.write(code)

print(f"Total changes: {changes}")
