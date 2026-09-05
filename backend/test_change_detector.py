from app.services.change_detector import (
    analyze_news,
    calculate_price_score,
    calculate_significance,
)


def test_high_price_movement():
    assert calculate_price_score(3.5) == 40


def test_combined_significance_includes_news():
    result = calculate_significance(3.2, 2_000_000, 1_000_000, -0.8, 10)
    assert result["score"] == 95
    assert result["severity"] == "HIGH"
    assert result["signals"]["news_score"] == 10


def test_negative_news_is_high_impact():
    result = analyze_news([{"headline": "Company warns of major loss after downgrade and recall"}])
    assert result["sentiment"] == "Negative"
    assert result["impact"] == "HIGH"
    assert result["score"] == 10
