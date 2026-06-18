"""
Tests for Hermes MerCu Signal Engine V2.
Covers: scoring, stage detection, OI analysis, coin classification, circuit breaker.
"""
import sys
import os
import pytest

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data_providers.hermes_mercu import (
    get_stage,
    get_oi_score,
    classify_coin,
    detect_stage,
    CoinType,
    SIGNAL_SCORES,
    STAGE_THRESHOLDS,
    CircuitBreaker,
    HermesSignalEngine,
)


# ============================================================
# 1. STAGE THRESHOLD TESTS
# ============================================================

class TestStageThresholds:
    def test_main_uptrend_confirmed(self):
        assert get_stage(15) == "主升确认"
        assert get_stage(12) == "主升确认"
        assert get_stage(20) == "主升确认"

    def test_bullish_start(self):
        assert get_stage(8) == "偏多启动"
        assert get_stage(10) == "偏多启动"
        assert get_stage(11) == "偏多启动"

    def test_accumulation(self):
        assert get_stage(4) == "吸筹/试盘"
        assert get_stage(5) == "吸筹/试盘"
        assert get_stage(7) == "吸筹/试盘"

    def test_oscillation(self):
        assert get_stage(0) == "震荡"
        assert get_stage(1) == "震荡"
        assert get_stage(3) == "震荡"

    def test_risk_zone(self):
        assert get_stage(-1) == "风险区"
        assert get_stage(-4) == "风险区"

    def test_distribution(self):
        assert get_stage(-5) == "派发/出货"
        assert get_stage(-10) == "派发/出货"
        assert get_stage(-50) == "派发/出货"


# ============================================================
# 2. OI SCORE TESTS (文档第三节)
# ============================================================

class TestOIScoring:
    def test_5m_noise(self):
        assert get_oi_score(1.5, "5m") == 0  # <2% is noise
        assert get_oi_score(-1.5, "5m") == 0

    def test_5m_entry(self):
        assert get_oi_score(4, "5m") == 1   # 3-5% 有资金进场
        assert get_oi_score(-4, "5m") == -1

    def test_5m_strong(self):
        assert get_oi_score(7, "5m") == 2   # 5-8% 明显异动
        assert get_oi_score(10, "5m") == 3  # 8-12% 强操盘
        assert get_oi_score(15, "5m") == 4  # 12%+ 拉盘前兆

    def test_15m_institutional(self):
        assert get_oi_score(8, "15m") == 2  # 5-10% 主力动作
        assert get_oi_score(12, "15m") == 3 # 10-15% 主升/逼空
        assert get_oi_score(20, "15m") == 5 # 15%+ 妖币级别

    def test_1h_trend(self):
        assert get_oi_score(8, "1h") == 2   # 5-10% 趋势增强
        assert get_oi_score(15, "1h") == 3  # 10-20% 强控盘
        assert get_oi_score(25, "1h") == 4  # 20-30% 妖币启动

    def test_1h_negative_benign(self):
        assert get_oi_score(-8, "1h") == -1 # -10%以内 正常降杠杆

    def test_1h_negative_serious(self):
        assert get_oi_score(-15, "1h") == -2  # 洗盘/爆仓
        assert get_oi_score(-25, "1h") == -3  # 主力撤离


# ============================================================
# 3. COIN CLASSIFICATION TESTS (文档第一节)
# ============================================================

class TestCoinClassification:
    def test_known_yaobi(self):
        assert classify_coin("COAI") == CoinType.YAOBI_CONTROL
        assert classify_coin("MEGA") == CoinType.YAOBI_CONTROL
        assert classify_coin("BEAT") == CoinType.YAOBI_CONTROL

    def test_known_sentiment(self):
        assert classify_coin("TRADOOR") == CoinType.SENTIMENT_HARVEST
        assert classify_coin("ESPORTS") == CoinType.SENTIMENT_HARVEST

    def test_known_institutional(self):
        assert classify_coin("TAO") == CoinType.INSTITUTIONAL_TREND
        assert classify_coin("SUI") == CoinType.INSTITUTIONAL_TREND

    def test_known_high_distribution(self):
        assert classify_coin("TRUMP") == CoinType.HIGH_DISTRIBUTION

    def test_unknown_with_micro_coin_cohort(self):
        assert classify_coin("NEWCOIN", cohort_label="微币") == CoinType.YAOBI_CONTROL

    def test_unknown_with_whipsaw(self):
        assert classify_coin("NEWCOIN", tags=["WHIPSAW"]) == CoinType.SENTIMENT_HARVEST

    def test_unknown_default(self):
        assert classify_coin("UNKNOWNCOIN", cohort_label=None) == CoinType.INSTITUTIONAL_TREND


# ============================================================
# 4. STAGE DETECTION TESTS (文档第四节)
# ============================================================

class TestStageDetection:
    def test_accumulation(self):
        events = [
            {"main_dim_label": "底部吸筹", "main_dim": "state", "main_direction": 1},
            {"main_dim_label": "现货托底", "main_dim": "state", "main_direction": 1},
            {"main_dim_label": "OI 暴涨", "main_dim": "oi", "main_direction": 1, "pct_to_ref": 6},
        ]
        result = detect_stage(events)
        assert "吸筹" in result.stage
        assert result.confidence >= 50

    def test_washout(self):
        events = [
            {"main_dim_label": "OI 暴跌", "main_dim": "oi", "main_direction": -1, "pct_to_ref": -8},
            {"main_dim_label": "现货托底", "main_dim": "state", "main_direction": 1},
            {"main_dim_label": "Vol 爆发", "main_dim": "vol", "main_direction": 1},
        ]
        result = detect_stage(events)
        assert result.stage == "洗盘期"

    def test_main_uptrend(self):
        events = [
            {"main_dim_label": "多头共振", "main_dim": "state", "main_direction": 1},
            {"main_dim_label": "OI 暴涨", "main_dim": "oi", "main_direction": 1, "pct_to_ref": 12},
            {"main_dim_label": "Vol 爆发", "main_dim": "vol", "main_direction": 1},
            {"main_dim_label": "现货托底", "main_dim": "state", "main_direction": 1},
        ]
        result = detect_stage(events)
        assert result.stage == "主升期"
        assert "右侧确认" in result.action

    def test_top_distribution(self):
        events = [
            {"main_dim_label": "顶部派发", "main_dim": "state", "main_direction": -1},
            {"main_dim_label": "OI背离", "main_dim": "oi", "main_direction": -1},
        ]
        result = detect_stage(events)
        assert result.stage == "派发期"
        assert "不接飞刀" in result.action

    def test_top_rush_whipsaw(self):
        events = [
            {"main_dim_label": "高陷阱", "main_dim": "state", "main_direction": -1},
            {"main_dim_label": "OI 暴涨", "main_dim": "oi", "main_direction": 1, "pct_to_ref": 15},
        ]
        result = detect_stage(events)
        assert result.stage == "赶顶期"
        assert "不追高" in result.action

    def test_crash(self):
        events = [
            {"main_dim_label": "OI 暴跌", "main_dim": "oi", "main_direction": -1, "pct_to_ref": -15},
            {"main_dim_label": "现货流出", "main_dim": "state", "main_direction": -1},
        ]
        result = detect_stage(events)
        assert result.stage == "出货崩盘期"

    def test_neutral(self):
        events = [
            {"main_dim_label": "Vol 爆发", "main_dim": "vol", "main_direction": 1},
        ]
        result = detect_stage(events)
        assert result.stage == "震荡"

    def test_partial_bull(self):
        events = [
            {"main_dim_label": "多头共振", "main_dim": "state", "main_direction": 1},
        ]
        result = detect_stage(events)
        assert "偏多" in result.stage or result.stage == "震荡"


# ============================================================
# 5. SIGNAL SCORES TESTS (文档第五节)
# ============================================================

class TestSignalScores:
    def test_all_scores_defined(self):
        """Verify all 21 signal types from the document are defined."""
        required = [
            "底部吸筹", "现货托底", "多头共振",
            "OI暴涨_5_10", "OI暴涨_10_plus", "OI暴涨_15_plus",
            "Vol爆发", "Vol极端放大",
            "大笔买入挂单", "空头被挤压", "逼空",
            "中陷阱后拉回",
            "高陷阱单次", "连续高陷阱", "顶部派发",
            "OI背离", "现货净流出",
            "OI暴跌_10_plus", "OI暴跌_20_plus", "多头爆仓",
        ]
        for signal in required:
            assert signal in SIGNAL_SCORES, f"Missing signal: {signal}"

    def test_bull_signals_positive(self):
        assert SIGNAL_SCORES["底部吸筹"] > 0
        assert SIGNAL_SCORES["多头共振"] > 0
        assert SIGNAL_SCORES["现货托底"] > 0

    def test_bear_signals_negative(self):
        assert SIGNAL_SCORES["顶部派发"] < 0
        assert SIGNAL_SCORES["OI背离"] < 0
        assert SIGNAL_SCORES["多头爆仓"] < 0

    def test_stage_thresholds_ordered(self):
        thresholds = [t for t, _ in STAGE_THRESHOLDS]
        assert thresholds == sorted(thresholds, reverse=True), "Should be descending"


# ============================================================
# 6. CIRCUIT BREAKER TESTS
# ============================================================

class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        assert not cb.is_open

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_open

    def test_resets_after_success(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.01)
        for _ in range(3):
            cb.record_failure()
        import time
        time.sleep(0.02)
        cb.record_success()
        assert not cb.is_open


# ============================================================
# 7. ENGINE INTEGRATION TEST
# ============================================================

class TestEngineIntegration:
    def test_score_events_bull(self):
        engine = HermesSignalEngine()
        events = [
            {"main_dim_label": "OI 暴涨", "main_dim": "oi", "main_direction": 1,
             "pct_to_ref": 12, "main_window": "15m", "grade": "SS"},
            {"main_dim_label": "Vol 爆发", "main_dim": "vol", "main_direction": 1,
             "pct_to_ref": 15, "main_window": "1h", "grade": "S"},
        ]
        score, triggered = engine.score_events("TEST", events)
        assert score > 0, f"Bull events should give positive score, got {score}"
        assert len(triggered) >= 2

    def test_score_events_bear(self):
        engine = HermesSignalEngine()
        events = [
            {"main_dim_label": "OI 暴跌", "main_dim": "oi", "main_direction": -1,
             "pct_to_ref": -15, "main_window": "15m", "grade": "SS"},
        ]
        score, triggered = engine.score_events("TEST", events)
        assert score < 0, f"Bear events should give negative score, got {score}"

    def test_analyze_coin_complete(self):
        engine = HermesSignalEngine()
        events = [
            {"main_dim_label": "底部吸筹", "main_dim": "state", "main_direction": 1,
             "pct_to_ref": 0, "main_window": "", "grade": "", "cohort_label": "微币"},
            {"main_dim_label": "OI 暴涨", "main_dim": "oi", "main_direction": 1,
             "pct_to_ref": 8, "main_window": "15m", "grade": "S"},
            {"main_dim_label": "Vol 爆发", "main_dim": "vol", "main_direction": 1,
             "pct_to_ref": 10, "main_window": "1h", "grade": "A"},
        ]
        result = engine.analyze_coin("COAI", events)
        assert result.symbol == "COAI"
        assert result.coin_type == CoinType.YAOBI_CONTROL
        assert result.score > 0
        assert result.direction in ("LONG", "NEUTRAL")
        assert "吸筹" in result.stage or result.stage in ("偏多启动", "吸筹/试盘", "震荡")


# ============================================================
# 8. EDGE CASES
# ============================================================

class TestEdgeCases:
    def test_empty_events(self):
        engine = HermesSignalEngine()
        score, triggered = engine.score_events("TEST", [])
        assert score == 0
        assert triggered == []

    def test_unknown_coin(self):
        result = classify_coin("ZZZNEWCOIN123", cohort_label=None, tags=[])
        assert result == CoinType.INSTITUTIONAL_TREND

    def test_boundary_oi_pct(self):
        # Exact boundary values
        assert get_oi_score(3.0, "5m") == 1   # Lower bound of 3-5%
        assert get_oi_score(4.9, "5m") == 1   # Just below 5%
        assert get_oi_score(5.0, "5m") == 2   # Lower bound of 5-8%
        assert get_oi_score(11.9, "5m") == 3  # Just below 12%
        assert get_oi_score(12.0, "5m") == 4  # 12%+

    def test_stage_all_thresholds(self):
        # Verify all thresholds map correctly
        test_cases = [
            (20, "主升确认"),
            (9, "偏多启动"),
            (5, "吸筹/试盘"),
            (2, "震荡"),
            (-2, "风险区"),
            (-8, "派发/出货"),
        ]
        for score, expected in test_cases:
            assert get_stage(score) == expected, f"Score {score} should be {expected}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])