"""Jin10 macro/news integration - optional, graceful fallback."""
import sys, os, time

class Jin10Bridge:
    """Bridge to V1's jin10_client if available, otherwise no-op."""
    def __init__(self):
        self.available = False
        try:
            v1_path = '/home/ubuntu/scripts/agents'
            if v1_path not in sys.path:
                sys.path.insert(0, v1_path)
            from jin10_client import macro_score, news_score
            self._macro_score = macro_score
            self._news_score = news_score
            self.available = True
        except ImportError:
            pass

    def macro_score(self):
        """Returns (score, reasons) or (0, [])."""
        if not self.available:
            return 0, []
        try:
            return self._macro_score()
        except Exception:
            return 0, []

    def news_score(self):
        """Returns (score, headlines) or (0, [])."""
        if not self.available:
            return 0, []
        try:
            return self._news_score()
        except Exception:
            return 0, []

    def combined_bonus(self):
        """Combined jin10 bonus for signal scoring."""
        bonus = 0
        reasons = []
        if not self.available:
            return 0, []
        try:
            ms, mreasons = self.macro_score()
            if ms != 0:
                bonus += ms
                reasons.extend(mreasons[:2])
            ns, headlines = self.news_score()
            if abs(ns) >= 6:
                bonus += ns // 2
                reasons.extend(headlines[:2])
        except Exception:
            pass
        return bonus, reasons
