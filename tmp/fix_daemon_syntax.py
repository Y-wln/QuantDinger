import re

path = '/home/ubuntu/hermes-v2/daemon.py'
with open(path) as f:
    content = f.read()

# Fix 1: main signal - merge try blocks
old = 'try: track(sig["symbol"], sig["direction"], sig["score"], sig["price"], "main")\n            try: signal_confirmed(None, sig["symbol"], sig["direction"], sig["score"], sig["price"], "main", sig.get("reasons",{}))\n            except: pass\n            except: pass'
new = 'try:\n                track(sig["symbol"], sig["direction"], sig["score"], sig["price"], "main")\n                signal_confirmed(None, sig["symbol"], sig["direction"], sig["score"], sig["price"], "main", sig.get("reasons",{}))\n            except: pass'
content = content.replace(old, new)

# Fix 2: mercu signal
old2 = 'try: track(sym, ms["direction"], ms["score"], px, "mercu", ms.get("reasons",[]))\n                                        try: signal_confirmed(None, sym, ms["direction"], ms["score"], px, "mercu", ms.get("reasons",[]))\n                                        except: pass\n                    except: pass'
new2 = 'try:\n                        track(sym, ms["direction"], ms["score"], px, "mercu", ms.get("reasons",[]))\n                        signal_confirmed(None, sym, ms["direction"], ms["score"], px, "mercu", ms.get("reasons",[]))\n                    except: pass'
content = content.replace(old2, new2)

# Fix 3: yaobi - check if it has try/except issue
old3 = 'try: track(ys["symbol"], ys["direction"], ys["score"], ys["price"], "yaobi", ys.get("reasons",[])); signal_confirmed(None, ys["symbol"], ys["direction"], ys["score"], ys["price"], "yaobi", ys.get("reasons",[]))\n                except: pass'
new3 = 'try:\n                    track(ys["symbol"], ys["direction"], ys["score"], ys["price"], "yaobi", ys.get("reasons",[]))\n                    signal_confirmed(None, ys["symbol"], ys["direction"], ys["score"], ys["price"], "yaobi", ys.get("reasons",[]))\n                except: pass'
if old3 in content:
    content = content.replace(old3, new3)

# Fix 4: lightning
old4 = 'try: track(fs["symbol"], fs["direction"], fs["score"], fs["price"], "lightning", fs.get("reasons",[])); signal_confirmed(None, fs["symbol"], fs["direction"], fs["score"], fs["price"], "lightning", fs.get("reasons",[]))\n                except: pass'
new4 = 'try:\n                    track(fs["symbol"], fs["direction"], fs["score"], fs["price"], "lightning", fs.get("reasons",[]))\n                    signal_confirmed(None, fs["symbol"], fs["direction"], fs["score"], fs["price"], "lightning", fs.get("reasons",[]))\n                except: pass'
if old4 in content:
    content = content.replace(old4, new4)

with open(path, 'w') as f:
    f.write(content)
print('Syntax fixes applied')
