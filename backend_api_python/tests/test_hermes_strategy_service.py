"""
Tests for Hermes Strategy Service.
Covers: position management, signal processing, cooldowns, risk limits.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data_providers.hermes_mercu import (
    HermesSignalEngine, CoinType, get_stage
)
from app.services.hermes_strategy_service import (
    HermesStrategyService,
    HermesPosition,
    HERMES_MAX_POSITIONS,
    HERMES_MIN_SCORE_LONG,
)


class TestHermesPosition:
    def test_long_pnl(self):
        pos = HermesPosition(
            symbol="BTC", direction="LONG", entry_price=100,
            entry_time=None, size_usd=1000, score=12,
            stage="主升确认", coin_type="机构趋势型"
        )
        assert pos.unrealized_pnl_pct(105) == 0.05
        assert pos.unrealized_pnl_pct(95) == -0.05

    def test_short_pnl(self):
        pos = HermesPosition(
            symbol="BTC", direction="SHORT", entry_price=100,
            entry_time=None, size_usd=1000, score=-10,
            stage="派发/出货", coin_type="高位派发型"
        )
        assert pos.unrealized_pnl_pct(95) == 0.05  # Short profits when price drops
        assert pos.unrealized_pnl_pct(105) == -0.05


class TestHermesStrategyService:
    def test_initial_state(self):
        svc = HermesStrategyService()
        status = svc.get_status()
        assert status["positions"] == 0
        assert status["max_positions"] == HERMES_MAX_POSITIONS
        assert "running" in status

    def test_position_limit(self):
        svc = HermesStrategyService()
        # Manually add positions to hit limit
        for i in range(HERMES_MAX_POSITIONS):
            svc.positions[f"COIN{i}"] = HermesPosition(
                symbol=f"COIN{i}", direction="LONG", entry_price=0,
                entry_time=None, size_usd=0, score=10,
                stage="主升确认", coin_type="妖币控盘型"
            )
        assert len(svc.positions) == HERMES_MAX_POSITIONS

        # Should not add more (logic in _process_signals checks limit)
        signal = {"symbol": "NEWCOIN", "direction": "LONG", "score": 15,
                  "stage": "主升确认", "coin_type": "妖币控盘型", "price": 1.0}
        svc._process_signals([signal])
        assert "NEWCOIN" not in svc.positions  # Should not open because at limit

    def test_cooldown_prevents_reopen(self):
        svc = HermesStrategyService()
        svc._set_cooldown("COAI")
        assert svc._is_cooldown("COAI") == True

    def test_cooldown_expires(self):
        svc = HermesStrategyService()
        # Monkey-patch cooldown to expire faster
        import app.services.hermes_strategy_service as hss
        old_cooldown = hss.HERMES_COOLDOWN_MINUTES
        hss.HERMES_COOLDOWN_MINUTES = 0  # Expire immediately

        svc._set_cooldown("COAI")
        time.sleep(0.01)
        assert svc._is_cooldown("COAI") == False

        hss.HERMES_COOLDOWN_MINUTES = old_cooldown

    def test_signal_history_limits(self):
        svc = HermesStrategyService()
        svc._max_history = 5
        for i in range(10):
            svc._signal_history.append({"symbol": f"COIN{i}", "_logged_at": time.time()})
        svc._log_signals([{"symbol": "NEW"}])  # triggers trim
        assert len(svc._signal_history) <= svc._max_history + 1

    def test_stop_loss_calculation(self):
        pos = HermesPosition(
            symbol="BTC", direction="LONG", entry_price=100,
            entry_time=None, size_usd=1000, score=12,
            stage="主升确认", coin_type="机构趋势型",
            stop_loss=95
        )
        # If price drops to stop loss, should close
        assert pos.unrealized_pnl_pct(95) == -0.05  # -5%, hit stop


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])