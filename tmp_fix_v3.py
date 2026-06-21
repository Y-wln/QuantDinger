import subprocess, os

path = "/app/app/services/hermes_strategies/__init__.py"
result = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "cat", path], capture_output=True, text=True)
content = result.stdout

old_marker = "def mercu_poll_loop():"
idx = content.find(old_marker)
if idx < 0:
    print("MARKER NOT FOUND")
    exit(1)

# Find the block: from "def mercu_poll_loop():" to the next "runner._running = True" or end of function
end_marker = 'runner._running = True'
end_idx = content.find(end_marker, idx)
if end_idx < 0:
    end_marker = '# 4. Start health reporter'
    end_idx = content.find(end_marker, idx)
    
print(f"Block from {idx} to {end_idx}")
old_block = content[idx:end_idx]

new_block = """def mercu_poll_loop():
            _log.info("MerCu poll thread started")
            while True:
                try:
                    data = bridge.fetch()
                    _pc["count"] += 1
                    
                    has_signals = bool(data and (data.get("anomalies") or data.get("surge")))
                    artifact_count = (
                        len(data.get("anomalies", [])) + len(data.get("surge", [])) + 
                        len(data.get("plaza", [])) + len(data.get("deep", []))
                    ) if data else 0
                    
                    if not has_signals:
                        _pc["empty_streak"] += 1
                        if _pc["empty_streak"] <= 3 or _pc["empty_streak"] % 10 == 0:
                            _log.info(f"MerCu poll #{_pc[\"count\"]}: {artifact_count} arts, 0 sigs (streak={_pc[\"empty_streak\"]})")
                    else:
                        _pc["empty_streak"] = 0
                        _log.info(f"MerCu poll #{_pc[\"count\"]}: {artifact_count} arts, has_signals")
                    
                    bus = EventBus.get()
                    bus.emit(Event(type=EventType.MERCU_DATA, data=data, source="mercu_bridge"))
                    
                    if bridge.engine:
                        engine_signals = bridge.engine.generate_signals()
                        if engine_signals:
                            _log.info(f"Engine signals: {len(engine_signals)}")
                            data["engine_signals"] = engine_signals
                            for es in engine_signals:
                                bus.emit(Event(type=EventType.SIGNAL_GENERATED, data=es, source="engine"))
                    
                    runner._run_cycle(mercu_data_provider=lambda: data)
                    _pc["errors"] = 0
                except Exception as e:
                    _pc["errors"] += 1
                    _log.error(f"MerCu poll err (c={_pc[\"count\"]} e={_pc[\"errors\"]}): {e}")
                    if _pc["errors"] > 10:
                        _log.critical("10+ errs, resetting bridge")
                        bridge.reset_engine()
                        _pc["errors"] = 0
                time.sleep(30)
        
        def watchdog_loop():
            _log.info("MerCu watchdog started")
            while True:
                time.sleep(60)
                try:
                    if not poll_thread.is_alive():
                        _log.critical("POLL DIED! Restarting...")
                        nt = threading.Thread(target=mercu_poll_loop, daemon=True, name="mercu-poll")
                        nt.start()
                except Exception as e:
                    _log.error(f"Watchdog err: {e}")
        
        _pc = {"count": 0, "errors": 0, "empty_streak": 0}
"""

new_content = content[:idx] + new_block + content[end_idx:]

with open("/tmp/init_v3_new.py", "w", encoding="utf-8") as f:
    f.write(new_content)

result = subprocess.run(["sudo", "docker", "cp", "/tmp/init_v3_new.py", f"hermes-backend:{path}"], capture_output=True, text=True)
print(f"cp result: {result.returncode} {result.stderr}")

# Verify
result2 = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "grep", "-c", "watchdog_loop", path], capture_output=True, text=True)
print(f"Verification: watchdog_loop found {result2.stdout.strip()} times")
print("DONE")
