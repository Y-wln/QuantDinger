"""
Tests for Hermes-QuantDinger full integration.
Covers: execution, notifications, portfolio, backtest, dashboard.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app.services.hermes_integration as integ


class TestSymbolNormalization:
    def test_simple_symbol(self):
        assert integ._normalize_hermes_symbol("BTC") == "BTC/USDT"

    def test_with_dollar_sign(self):
        assert integ._normalize_hermes_symbol("$ETH") == "ETH/USDT"

    def test_already_normalized(self):
        assert integ._normalize_hermes_symbol("SOL/USDT") == "SOL/USDT"

    def test_case_insensitive(self):
        assert integ._normalize_hermes_symbol("btc") == "BTC/USDT"


class TestBacktestDataPrep:
    def test_empty_history(self):
        assert integ.hermes_prepare_backtest_data([]) == []

    def test_single_signal(self):
        history = [{
            "symbol": "BTC", "direction": "LONG", "score": 15,
            "stage": "主升确认", "price": 64000, "timestamp": "2026-06-18T10:00:00",
            "signals": ["OI暴涨", "Vol爆发"]
        }]
        result = integ.hermes_prepare_backtest_data(history)
        assert len(result) == 1
        assert result[0]["signal_type"] == "buy"
        assert result[0]["score"] == 15

    def test_short_signal(self):
        history = [{
            "symbol": "BEAT", "direction": "SHORT", "score": -12,
            "stage": "派发/出货", "price": 7.0, "timestamp": "",
            "signals": ["顶部派发"]
        }]
        result = integ.hermes_prepare_backtest_data(history)
        assert result[0]["signal_type"] == "sell"


class TestFeishuCardFormat:
    def test_empty_signals(self):
        card = integ.hermes_format_feishu_card([])
        assert card["msg_type"] == "text"
        assert "暂无信号" in card["content"]["text"]

    def test_with_signals(self):
        signals = [
            {"symbol": "BTC", "direction": "LONG", "score": 15,
             "stage": "主升确认", "price": 64000, "signals": ["OI暴涨", "Vol爆发"]},
            {"symbol": "ETH", "direction": "SHORT", "score": -8,
             "stage": "派发/出货", "price": 1680, "signals": ["OI暴跌"]},
        ]
        card = integ.hermes_format_feishu_card(signals)
        assert card["msg_type"] == "interactive"
        assert "card" in card


class TestDashboardMetrics:
    def test_metrics_structure(self):
        metrics = integ.hermes_get_dashboard_metrics()
        # Should return a dict even if service isn't running
        assert isinstance(metrics, dict)
        # If error, it should have "error" key
        # If running, it should have expected keys
        if "error" not in metrics:
            assert "active_positions" in metrics


class TestIntegrationStatus:
    def test_integration_status(self):
        status = integ.integrate_hermes_with_quantdinger()
        assert isinstance(status, dict)
        assert "execution" in status
        assert "notification" in status
        assert "portfolio" in status
        assert "backtest" in status


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])