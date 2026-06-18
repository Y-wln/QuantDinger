"""
USDT Payment service stub (payment features removed).
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class USDTOrderWorker:
    """Stub - no USDT payment processing."""
    def start(self): pass
    def stop(self): pass


_singleton = None


def get_usdt_order_worker():
    global _singleton
    if _singleton is None:
        _singleton = USDTOrderWorker()
    return _singleton


def get_usdt_payment_service():
    return None
