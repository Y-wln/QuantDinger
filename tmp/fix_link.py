path = "/home/ubuntu/hermes-v2/services/pipeline_tracker.py"
with open(path, encoding="utf-8-sig") as f:
    content = f.read()

# Fix early_detected: dedup by symbol+direction before creating new entry
old = "    if pid in d['active']:\n        return pid\n    \n    pipe = {"
new = """    # Dedup: check if same symbol+direction already exists
    for ep, epipe in list(d.get("active",{}).items()):
        if epipe.get("symbol") == symbol.replace("USDT","") and epipe.get("direction") == direction:
            # Update existing early entry instead of creating duplicate
            if not epipe.get("signal_time"):
                epipe["early_time"] = time.time()
                epipe["early_time_str"] = datetime.now(BJT).strftime("%m/%d %H:%M:%S")
                epipe["early_price"] = price
                epipe["early_source"] = source
                epipe["early_pattern"] = pattern
                epipe["early_indicators"] = indicators or {}
            _save(d)
            return ep
    
    pipe = {"""
content = content.replace(old, new)

# Also fix signal_confirmed: update ALL matching early entries
old2 = "            if not epipe.get(\"signal_time\"):\n                epipe[\"status\"] = \"active\"\n                epipe[\"signal_time\"] = time.time()\n                epipe[\"signal_time_str\"] = datetime.now(BJT).strftime(\"%m/%d %H:%M:%S\")\n                epipe[\"signal_price\"] = price\n                epipe[\"signal_score\"] = score\n                epipe[\"signal_source\"] = source\n                epipe[\"signal_indicators\"] = indicators or {}\n            _save(d)\n            return pid"
new2 = """            epipe["status"] = "active"
            if not epipe.get("signal_time"):
                epipe["signal_time"] = time.time()
                epipe["signal_time_str"] = datetime.now(BJT).strftime("%m/%d %H:%M:%S")
                epipe["signal_price"] = price
                epipe["signal_score"] = score
                epipe["signal_source"] = source
                epipe["signal_indicators"] = indicators or {}
            # Link ALL other early entries for this symbol
            for ep2, epipe2 in list(d.get("active",{}).items()):
                if ep2 != ep and epipe2.get("symbol") == symbol.replace("USDT","") and epipe2.get("direction") == direction and not epipe2.get("signal_time"):
                    epipe2["status"] = "active"
                    epipe2["signal_time"] = time.time()
                    epipe2["signal_time_str"] = datetime.now(BJT).strftime("%m/%d %H:%M:%S")
                    epipe2["signal_price"] = price
                    epipe2["signal_score"] = score
                    epipe2["signal_source"] = source
                    epipe2["signal_indicators"] = indicators or {}
            _save(d)
            return pid"""
content = content.replace(old2, new2)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Link fix applied")
