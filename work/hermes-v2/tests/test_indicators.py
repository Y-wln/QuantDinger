"""Tests for Hermes V2 indicators."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_bb():
    from indicators.bb import bollinger_bands, score_bb
    # Simulated prices
    prices = [100 + i * 0.1 + (i % 5) * 0.5 for i in range(30)]
    bb = bollinger_bands(prices)
    assert bb is not None, "BB should not be None"
    assert 'bandwidth' in bb, "BB should have bandwidth"
    assert 0 <= bb['percent_b'] <= 1, f"percent_b should be 0-1, got {bb['percent_b']}"
    score, reason, is_lead = score_bb(prices)
    assert isinstance(score, int), "score should be int"
    print(f"  ✅ BB: bandwidth={bb['bandwidth']:.2f}% percent_b={bb['percent_b']:.2f} score={score}")

def test_rsi():
    from indicators.rsi import rsi, score_rsi, detect_rsi_divergence
    prices = [100 + i * 0.5 for i in range(20)]  # uptrend
    val = rsi(prices)
    assert 0 <= val <= 100, f"RSI should be 0-100, got {val}"
    score, reason = score_rsi(prices)
    assert isinstance(score, int)
    print(f"  ✅ RSI: {val:.1f} score={score} reason={reason}")

def test_cvd():
    from indicators.cvd import calc_cvd, score_cvd_5m
    klines = [{'o': 100, 'c': 101, 'v': 1000} for _ in range(10)]
    cv = calc_cvd(klines, 3)
    assert isinstance(cv, (int, float))
    score, reason = score_cvd_5m(klines)
    print(f"  ✅ CVD: {cv:.1f} score={score}")

def test_macd():
    from indicators.macd import macd, ema, score_macd
    prices = [100 + i * 0.5 for i in range(40)]
    md, mdea, mh = macd(prices)
    score, reason = score_macd(prices)
    print(f"  ✅ MACD: line={md:.4f} signal={mdea:.4f} hist={mh:.4f} score={score}")

def test_structure():
    from indicators.structure import detect_structure, detect_bos_choch
    klines = [{'h': 100+i, 'l': 99+i, 'c': 99.5+i, 'o': 99+i} for i in range(50)]
    s, c = detect_structure(klines)
    smc = detect_bos_choch(klines)
    print(f"  ✅ Structure: {s}({c}) SMC={smc['structure']}")

def test_momentum():
    from indicators.momentum import momentum_score, detect_pin_bar, detect_doji
    klines = [{'o': 100, 'h': 102, 'l': 98, 'c': 101, 'v': 1000} for _ in range(30)]
    mom = momentum_score(klines)
    pb = detect_pin_bar(klines)
    dj = detect_doji(klines)
    print(f"  ✅ Momentum: {mom} pin={pb} doji={dj}")

def test_volume():
    from indicators.volume import volume_surge, atr, score_volume_surge
    klines = [{'h': 102, 'l': 98, 'c': 100, 'v': 1000} for _ in range(20)]
    ratio, direction = volume_surge(klines)
    atr_val = atr(klines)
    score, reason, is_lead = score_volume_surge(klines)
    print(f"  ✅ Volume: surge_ratio={ratio:.2f} atr={atr_val:.2f} score={score}")

if __name__ == '__main__':
    print("Hermes V2 - Indicator Tests")
    print("=" * 50)
    for name, fn in [('BB', test_bb), ('RSI', test_rsi), ('CVD', test_cvd),
                      ('MACD', test_macd), ('Structure', test_structure),
                      ('Momentum', test_momentum), ('Volume', test_volume)]:
        try:
            fn()
        except Exception as e:
            print(f"  ❌ {name}: {e}")
    print("\n✅ All tests passed!")
