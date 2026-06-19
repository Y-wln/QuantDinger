"""Price Provider - Reads from local price file pushed by Windows agent."""
import os, json, time, logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)
PRICE_FILE = "/tmp/hermes_live_prices.json"

class PriceProvider:
    def __init__(self):
        self._cache: Dict[str, float] = {}
        self._cache_ts: float = 0

    def _load_from_file(self) -> Dict[str, float]:
        if not os.path.exists(PRICE_FILE):
            return {}
        try:
            with open(PRICE_FILE) as f:
                data = json.load(f)
            return {k.upper(): float(v) for k, v in data.items() if v}
        except:
            return {}

    def get_prices(self, symbols: list) -> Dict[str, float]:
        prices = self._load_from_file()
        if prices:
            self._cache = prices
            self._cache_ts = time.time()
        return {s: self._cache.get(s.upper(), 0) for s in symbols}

_price_provider: Optional[PriceProvider] = None
def get_price_provider() -> PriceProvider:
    global _price_provider
    if _price_provider is None:
        _price_provider = PriceProvider()
    return _price_provider
