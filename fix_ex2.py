with open(r"C:\Users\ZhuanZ\Documents\Codex\QuantDinger\tmp_selfcheck_fixed.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "from app.utils.db import get_db"
new = "from app.utils.db import get_db_connection"

content = content.replace(old, new)

old2 = 'rows = db.fetch_all("SELECT id, name, exchange_id, api_key_hint FROM qd_exchange_credentials")'
new2 = '''            cur = db.cursor()
            cur.execute("SELECT id, name, exchange_id, api_key_hint FROM qd_exchange_credentials")
            rows = cur.fetchall()
            cur.close()
            db.commit()  # no-op for SELECT, but required by psycopg2 protocol'''

# Replace the method body
old_body = '''    def _check_exchange(self) -> dict:
        """Check exchange connectivity (reads from DB, not env vars)."""
        try:
            from app.utils.db import get_db_connection
            db = get_db_connection()
            rows = db.fetch_all("SELECT id, name, exchange_id, api_key_hint FROM qd_exchange_credentials")
            if not rows:
                import os
                if os.getenv("BINANCE_API_KEY") or os.getenv("EXCHANGE_API_KEY"):
                    return {"status": "OK", "detail": "ENV credentials (legacy)"}
                return {"status": "NOT_CONFIGURED", "detail": "No exchange credentials in DB or ENV"}
            
            exchanges = []
            for r in rows:
                exchanges.append(f"{r['exchange_id']}({r['name']})")
            return {
                "status": "OK",
                "detail": f"{len(rows)} configured: {', '.join(exchanges)}"
            }
        except Exception as e:
            return {"status": "ERROR", "detail": str(e)[:100]}'''

new_body = '''    def _check_exchange(self) -> dict:
        """Check exchange connectivity (reads from DB, not env vars)."""
        try:
            from app.utils.db import get_db_connection
            with get_db_connection() as db:
                cur = db.cursor()
                cur.execute("SELECT id, name, exchange_id, api_key_hint FROM qd_exchange_credentials")
                rows = cur.fetchall()
                cur.close()
            if not rows:
                import os
                if os.getenv("BINANCE_API_KEY") or os.getenv("EXCHANGE_API_KEY"):
                    return {"status": "OK", "detail": "ENV credentials (legacy)"}
                return {"status": "NOT_CONFIGURED", "detail": "No exchange credentials in DB or ENV"}
            
            exchanges = []
            for r in rows:
                exchanges.append(f"{r[2]}({r[1]})")
            return {
                "status": "OK",
                "detail": f"{len(rows)} configured: {', '.join(exchanges)}"
            }
        except Exception as e:
            return {"status": "ERROR", "detail": str(e)[:100]}'''

if old_body in content:
    content = content.replace(old_body, new_body)
    print("Replaced exchange method body")
else:
    print("NOT FOUND")
    s = content.find("def _check_exchange")
    if s > 0:
        print(content[s:s+800])

with open(r"C:\Users\ZhuanZ\Documents\Codex\QuantDinger\tmp_selfcheck_fixed2.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Written")
