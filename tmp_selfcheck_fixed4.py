"""
SelfCheck V1 - 系统自检
=========================
QD-native system health monitor.
Checks all components and reports status.

Monitors:
1. MerCu data freshness
2. Strategy service health
3. Scanner status
4. Tracker integrity
5. Exchange connectivity
"""
from __future__ import annotations

import os
import time
import logging
import threading
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

from app.utils.logger import get_logger

logger = get_logger(__name__)
BJT = timezone(timedelta(hours=8))

CHECK_INTERVAL = int(os.getenv("SELFCHECK_INTERVAL", "600"))  # 10 minutes
STALE_THRESHOLD = int(os.getenv("SELFCHECK_STALE", "300"))     # 5 min = stale


class SelfCheck:
    """System self-check monitor."""

    def __init__(self):
        self._last_check: float = 0
        self._results: Dict[str, dict] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="selfcheck")
        self._thread.start()
        logger.info("SelfCheck started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self):
        while self._running:
            try:
                self._results = self.run_check()
                self._last_check = time.time()
            except Exception as e:
                logger.error(f"SelfCheck error: {e}")
            time.sleep(CHECK_INTERVAL)

    def run_check(self) -> Dict[str, dict]:
        """Run a full system check."""
        results = {}
        now = time.time()

        # 1. MerCu data check
        try:
            from app.data_providers.hermes_mercu import get_hermes_engine
            engine = get_hermes_engine()
            cache_age = now - engine._cache_ts if engine._cache_ts > 0 else 99999
            results["mercu"] = {
                "status": "OK" if cache_age < STALE_THRESHOLD else "STALE",
                "cache_age_s": round(cache_age, 0),
                "detail": f"Cache age: {cache_age:.0f}s"
            }
        except Exception as e:
            results["mercu"] = {"status": "ERROR", "detail": str(e)[:100]}

        # 2. Strategy check (Hermes V3)
        try:
            from app.services.hermes_strategies import get_hermes_v3_status
            v3 = get_hermes_v3_status()
            if v3.get("status") == "not_started":
                results["strategy"] = {
                    "status": "STOPPED",
                    "positions": 0,
                    "detail": "V3 not started"
                }
            elif v3.get("status") == "error":
                results["strategy"] = {
                    "status": "ERROR",
                    "positions": 0,
                    "detail": v3.get("error", "unknown")[:100]
                }
            else:
                pos = v3.get("positions", {})
                pos_count = len(pos) if isinstance(pos, dict) else 0
                results["strategy"] = {
                    "status": "OK",
                    "positions": pos_count,
                    "detail": f"V3 running, subs={v3.get("event_bus_subscribers",0)}"
                }
        except Exception as e:
            results["strategy"] = {"status": "ERROR", "detail": str(e)[:100]}

        # 3. Yaobi scanner check
        try:
            from app.services.yaobi_scanner import get_yaobi_scanner
            scanner = get_yaobi_scanner()
            age = now - scanner._last_scan if scanner._last_scan > 0 else 99999
            results["yaobi"] = {
                "status": "OK" if age < STALE_THRESHOLD * 2 else "IDLE",
                "candidates": len(scanner._candidates),
                "detail": f"Last scan: {age:.0f}s ago, {len(scanner._candidates)} candidates"
            }
        except Exception as e:
            results["yaobi"] = {"status": "DISABLED", "detail": str(e)[:100]}

        # 4. Tracker check
        try:
            from app.services.pipeline_tracker import get_pipeline_tracker
            tracker = get_pipeline_tracker()
            status = tracker.get_status()
            results["tracker"] = {
                "status": "OK",
                "total": status["total"],
                "active": status["active"],
                "detail": f"Total={status['total']}, active={status['active']}"
            }
        except Exception as e:
            results["tracker"] = {"status": "DISABLED", "detail": str(e)[:100]}

        # 5. Exchange connectivity check
        results["exchange"] = self._check_exchange()

        # 6. Overall status
        errors = sum(1 for v in results.values() if v.get("status") in ("ERROR", "STALE"))
        warnings = sum(1 for v in results.values() if v.get("status") in ("STOPPED", "IDLE", "DISABLED"))
        overall = "HEALTHY" if errors == 0 and warnings <= 1 else "WARNING" if errors == 0 else "CRITICAL"

        results["overall"] = {
            "status": overall,
            "errors": errors,
            "warnings": warnings,
            "timestamp": datetime.now(BJT).isoformat(),
        }

        return results

    def _check_exchange(self) -> dict:
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
            return {"status": "ERROR", "detail": str(e)[:100]}

_selfcheck: Optional[SelfCheck] = None

def get_selfcheck() -> SelfCheck:
    global _selfcheck
    if _selfcheck is None:
        _selfcheck = SelfCheck()
    return _selfcheck
