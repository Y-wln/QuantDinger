# Fix mercu signals to include price
path = "/home/ubuntu/scripts/agents/mercu_signals.py"
with open(path, "r", encoding="utf-8-sig") as f:
    content = f.read()

# Fix: add price to signal dict
old = 'signals.append({"sym": sym, "dir": direction, "score": score, "reasons": reasons})'
new = 'price = fetch_price(sym + "USDT")\n                signals.append({"sym": sym, "dir": direction, "score": score, "reasons": reasons, "price": price or 0})'
content = content.replace(old, new)

# Also fix duplicate fetch_price calls in display (use the price we already have)
# The display section calls fetch_price again, which is wasteful but not broken
# Just fix the error for now

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("MerCu price field added")
