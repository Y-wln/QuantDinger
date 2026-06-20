# fix_v17_executor.py - fix ThreadPoolExecutor shutdown issue
path = "/home/ubuntu/scripts/agents/yaobi_pusher.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix: "ex.submit" -> create new executor for fast scan
old = "            fast_futures = {ex.submit(fast_check_1m, c): c for c in candidates[:8]}"
new = "            with ThreadPoolExecutor(max_workers=4) as fx:\n                fast_futures = {fx.submit(fast_check_1m, c): c for c in candidates[:8]}"
content = content.replace(old, new)

# Fix indentation of the for loop that follows
old2 = "            for f in as_completed(fast_futures, timeout=30):"
new2 = "                for f in as_completed(fast_futures, timeout=30):"
content = content.replace(old2, new2)

# Fix indentation of consequent lines
old3 = "                r = f.result()"
new3 = "                    r = f.result()"
content = content.replace(old3, new3)

old4 = "                if r:"
new4 = "                    if r:"
content = content.replace(old4, new4)

old5 = "                    sym, ptype, chg, vratio, price = r"
new5 = "                        sym, ptype, chg, vratio, price = r"
content = content.replace(old5, new5)

old6 = '                    sym_short = sym.replace("USDT","")'
new6 = '                        sym_short = sym.replace("USDT","")'
content = content.replace(old6, new6)

old7 = '                    fast_warnings.append'
new7 = '                        fast_warnings.append'
content = content.replace(old7, new7)

old8 = "            if fast_warnings:"
new8 = "                if fast_warnings:"
content = content.replace(old8, new8)

old9 = '                print("[YaobiV17] 1m fast warnings:'
new9 = '                    print("[YaobiV17] 1m fast warnings:'
content = content.replace(old9, new9)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Executor fix applied")
