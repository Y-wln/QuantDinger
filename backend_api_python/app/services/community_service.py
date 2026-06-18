"""
Community service stub (marketplace features removed).
Returns safe defaults so existing code paths don't break.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class CommunityService:
    """Stub community service - marketplace disabled."""

    def publish_script_template_from_strategy(self, *args, **kwargs):
        logger.info("Stub: publish_script_template (disabled)")
        return False, "Marketplace disabled", None

    def publish_bot_preset_from_strategy(self, *args, **kwargs):
        logger.info("Stub: publish_bot_preset (disabled)")
        return False, "Marketplace disabled", None

    def get_market_indicators(self, *args, **kwargs):
        return {"items": [], "total": 0}

    def get_indicator_detail(self, indicator_id: str):
        return None


_singleton: CommunityService | None = None


def get_community_service() -> CommunityService:
    global _singleton
    if _singleton is None:
        _singleton = CommunityService()
    return _singleton
