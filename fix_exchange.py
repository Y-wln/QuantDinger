import sys

# Read file as UTF-16 (PowerShell redirection encoding)
with open(r"C:\Users\ZhuanZ\Documents\Codex\QuantDinger\tmp_selfcheck_orig.py", "r", encoding="utf-16") as f:
    content = f.read()

old_start = "    def _check_exchange(self) -> dict:"
old_end = '            return {"status": "ERROR", "detail": str(e)[:100]}'

s = content.find(old_start)
e = content.find(old_end, s)

if s < 0 or e < 0:
    print(f"NOT FOUND: start={s} end={e}")
    # Print context
    if s > 0:
        print(content[s:s+800])
    sys.exit(1)

old_block = content[s:e + len(old_end)]

new_block = """    def _check_exchange(self) -> dict:
        \"\"\"Check exchange connectivity (reads from DB, not env vars).\"\"\"
        try:
            from app.utils.db import get_db
            db = get_db()
            rows = db.fetch_all("SELECT id, name, exchange_id, api_key_hint FROM qd_exchange_credentials")
            if not rows:
                import os
                if os.getenv("BINANCE_API_KEY") or os.getenv("EXCHANGE_API_KEY"):
                    return {"status": "OK", "detail": "ENV credentials (legacy)"}
                return {"status": "NOT_CONFIGURED", "detail": "No exchange credentials in DB or ENV"}
            
            exchanges = []
            for r in rows:
                exchanges.append(f\"{r['exchange_id']}({r['name']})\")
            return {
                "status": "OK",
                "detail": f\"{len(rows)} configured: {', '.join(exchanges)}\"
            }
        except Exception as e:
            return {"status": "ERROR", "detail": str(e)[:100]}"""

content = content.replace(old_block, new_block)
print(f"Replaced: {len(old_block)} -> {len(new_block)} chars")

# Write as UTF-8
with open(r"C:\Users\ZhuanZ\Documents\Codex\QuantDinger\tmp_selfcheck_fixed.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Written to tmp_selfcheck_fixed.py")
