import re

path = "/home/ubuntu/hermes-v2/daemon.py"
with open(path, encoding="utf-8-sig") as f:
    content = f.read()

# 1. Add pipeline_tracker import
old_import = "from services.v2_tracker import track, fetch_all_prices as tracker_fetch_prices"
new_import = old_import + "\nfrom services.pipeline_tracker import early_detected, signal_confirmed, take_snapshots"
content = content.replace(old_import, new_import)

# 2. Add signal_confirmed after main track()
old_main = 'try: track(sig["symbol"], sig["direction"], sig["score"], sig["price"], "main")\n            except: pass'
new_main = 'try:\n                track(sig["symbol"], sig["direction"], sig["score"], sig["price"], "main")\n                signal_confirmed(None, sig["symbol"], sig["direction"], sig["score"], sig["price"], "main", sig.get("reasons",{}))\n            except: pass'
content = content.replace(old_main, new_main)

# 3. Add signal_confirmed after mercu track()
old_mercu = 'try: track(sym, ms["direction"], ms["score"], px, "mercu", ms.get("reasons",[]))\n                    except: pass'
new_mercu = 'try:\n                        track(sym, ms["direction"], ms["score"], px, "mercu", ms.get("reasons",[]))\n                        signal_confirmed(None, sym, ms["direction"], ms["score"], px, "mercu", ms.get("reasons",[]))\n                    except: pass'
content = content.replace(old_mercu, new_mercu)

# 4. Add track + signal_confirmed after yaobi log write
old_yaobi = 'with open(YAOBI_LOG, "a") as f:\n                    f.write(json.dumps(ye) + "\\n")\n                print("  [{}] YAOBI {:5s} {:12s} Score:{:+4d}".format('
new_yaobi = 'with open(YAOBI_LOG, "a") as f:\n                    f.write(json.dumps(ye) + "\\n")\n                try:\n                    track(ys["symbol"], ys["direction"], ys["score"], ys["price"], "yaobi", ys.get("reasons",[]))\n                    signal_confirmed(None, ys["symbol"], ys["direction"], ys["score"], ys["price"], "yaobi", ys.get("reasons",[]))\n                except: pass\n                print("  [{}] YAOBI {:5s} {:12s} Score:{:+4d}".format('
content = content.replace(old_yaobi, new_yaobi)

# 5. Add track + signal_confirmed after lightning log write
old_flash = 'with open(LIGHTNING_LOG, "a") as f:\n                    f.write(json.dumps(fe) + "\\n")\n                print("  [{}] FLASH {:5s} {:12s} Score:{:+4d}".format('
new_flash = 'with open(LIGHTNING_LOG, "a") as f:\n                    f.write(json.dumps(fe) + "\\n")\n                try:\n                    track(fs["symbol"], fs["direction"], fs["score"], fs["price"], "lightning", fs.get("reasons",[]))\n                    signal_confirmed(None, fs["symbol"], fs["direction"], fs["score"], fs["price"], "lightning", fs.get("reasons",[]))\n                except: pass\n                print("  [{}] FLASH {:5s} {:12s} Score:{:+4d}".format('
content = content.replace(old_flash, new_flash)

# 6. Add take_snapshots every 5 cycles (backup for cron)
old_sleep = "time.sleep(max(0, cfg.get(\"scan_interval\", 60) - elapsed))"
new_sleep = "if cycle % 5 == 0:\n            try: take_snapshots()\n            except: pass\n        time.sleep(max(0, cfg.get(\"scan_interval\", 60) - elapsed))"
content = content.replace(old_sleep, new_sleep)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("daemon.py integration complete")
