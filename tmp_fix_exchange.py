import subprocess

path = "/app/app/services/selfcheck.py"
result = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "cat", path], capture_output=True, text=True)
content = result.stdout

old_exchange = """    def _check_exchange(self) -> dict:
        """Check exchange connectivity."""
        try:
            import os
            if not os.getenv("BINANCE_API_KEY") and not os.getenv("EXCHANGE_API_KEY"):
                return {"status": "NOT_CONFIGURED", "detail": "API keys not set (intentional)"}
            from app.services.live_trading.factory import create_client
            from app.services.live_trading.contracts import normalize_order_market_type
            client = create_client(
                {"exchange_id": "binance"},
                market_type=normalize_order_market_type("swap"),
            )
            if client and hasattr(client, "get_ticker"):
                ticker = client.get_ticker(symbol="BTCUSDT")
                if ticker:
                    return {
                        "status": "OK",
                        "btc_price": float(ticker.get("lastPrice", 0)),
                        "detail": "Binance futures connected"
                    }
            return {"status": "ERROR", "detail": "Exchange client returned no data"}
        except Exception as e:
            return {"status": "ERROR", "detail": str(e)[:100]}"""

new_exchange = """    def _check_exchange(self) -> dict:
        """Check exchange connectivity (reads from DB, not env vars)."""
        try:
            from app.utils.db import get_db
            db = get_db()
            rows = db.fetch_all("SELECT id, name, exchange_id, api_key_hint FROM qd_exchange_credentials")
            if not rows:
                # Fallback: check env vars for legacy config
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
            return {"status": "ERROR", "detail": str(e)[:100]}"""

if old_exchange in content:
    content = content.replace(old_exchange, new_exchange)
    print("Replaced exchange check -> DB")
else:
    print("Old exchange block NOT found!")
    idx = content.find("_check_exchange")
    if idx > 0:
        print(content[idx:idx+600])
    exit(1)

with open("/tmp/selfcheck_new2.py", "w", encoding="utf-8") as f:
    f.write(content)

result = subprocess.run(["sudo", "docker", "cp", "/tmp/selfcheck_new2.py", f"hermes-backend:{path}"], capture_output=True, text=True)
print(f"cp: {result.returncode}")

result2 = subprocess.run(["sudo", "docker", "exec", "hermes-backend", "python3", "-c",
    "import py_compile; py_compile.compile('/app/app/services/selfcheck.py', doraise=True); print('SYNTAX OK')"],
    capture_output=True, text=True)
print(result2.stdout)
print(result2.stderr)
