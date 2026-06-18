"""
Billing service stub (community/payment features removed).
Returns safe defaults so existing code paths don't break.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class BillingService:
    """Stub billing service - all users have unlimited access."""

    def get_membership_plans(self) -> list:
        return [{"id": "free", "name": "Free", "credits": 999999, "price": 0}]

    def get_user_billing_info(self, user_id: str) -> dict:
        return {
            "plan": "free",
            "credits": 999999,
            "vip_expires_at": None,
            "is_vip": False,
        }

    def add_credits(self, user_id: str, amount: int, remark: str = "", operator_id: str = ""):
        logger.info(f"Stub: add_credits user={user_id} amount={amount}")
        return True, {"credits": 999999}

    def set_credits(self, user_id: str, amount: int, remark: str = "", operator_id: str = ""):
        return True, {"credits": amount}

    def set_vip(self, user_id: str, expires_at, remark: str = "", operator_id: str = ""):
        logger.info(f"Stub: set_vip user={user_id}")
        return True, {"vip": True}

    def get_credits_log(self, user_id: str, page: int = 1, page_size: int = 20):
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    def check_credits(self, user_id: str, amount: int = 1) -> bool:
        return True

    def consume_credits(self, user_id: str, amount: int, remark: str = "") -> bool:
        return True


_singleton: BillingService | None = None


def get_billing_service() -> BillingService:
    global _singleton
    if _singleton is None:
        _singleton = BillingService()
    return _singleton
