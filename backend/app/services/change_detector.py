def calculate_price_score(percentage_change: float) -> int:
    change = abs(percentage_change)
    if change >= 3:
        return 40
    if change >= 2:
        return 25
    if change >= 1:
        return 15
    return 0


def calculate_volume_score(current_volume: float | None, average_volume: float | None) -> int:
    if not current_volume or not average_volume or average_volume <= 0:
        return 0
    ratio = current_volume / average_volume
    if ratio >= 2:
        return 25
    if ratio >= 1.5:
        return 18
    if ratio >= 1.2:
        return 10
    return 0


def calculate_market_score(stock_change: float, market_change: float | None) -> int:
    if market_change is None:
        return 0
    difference = abs(stock_change - market_change)
    if difference >= 3:
        return 20
    if difference >= 2:
        return 15
    if difference >= 1:
        return 10
    return 0


def analyze_news(articles: list[dict]) -> dict:
    positive_words = {"beat", "growth", "grow", "record", "surge", "upgrade", "profit", "strong", "launch", "approved"}
    negative_words = {"fall", "fell", "drop", "loss", "miss", "downgrade", "lawsuit", "cut", "weak", "warning", "recall", "layoff"}
    positive_hits = 0
    negative_hits = 0
    for article in articles:
        words = set((article.get("headline") or "").lower().replace("-", " ").split())
        positive_hits += len(words & positive_words)
        negative_hits += len(words & negative_words)

    if not articles:
        return {"score": 0, "sentiment": "Unknown", "impact": "None", "articles": []}
    if negative_hits > positive_hits:
        sentiment = "Negative"
    elif positive_hits > negative_hits:
        sentiment = "Positive"
    else:
        sentiment = "Neutral"
    strength = positive_hits + negative_hits
    impact = "HIGH" if strength >= 3 else "MEDIUM" if strength >= 1 else "LOW"
    score = 10 if impact == "HIGH" else 5 if impact == "MEDIUM" else 0
    return {"score": score, "sentiment": sentiment, "impact": impact, "articles": articles}


def calculate_significance(
    percentage_change: float,
    current_volume: float | None = None,
    average_volume: float | None = None,
    market_change: float | None = None,
    news_score: int = 0
):
    price_score = calculate_price_score(percentage_change)
    volume_score = calculate_volume_score(current_volume, average_volume)
    market_score = calculate_market_score(percentage_change, market_change)
    total_score = price_score + volume_score + market_score + news_score
    severity = "HIGH" if total_score >= 60 else "MEDIUM" if total_score >= 30 else "NORMAL"
    return {
        "score": total_score,
        "severity": severity,
        "signals": {
            "price_score": price_score,
            "volume_score": volume_score,
            "market_score": market_score,
            "news_score": news_score
        }
    }


def calculate_change(previous_price: float, current_price: float):
    if previous_price == 0:
        return {"absolute_change": 0, "percentage_change": 0, "severity": "NORMAL", "score": 0}
    absolute_change = current_price - previous_price
    percentage_change = (absolute_change / previous_price) * 100
    significance = calculate_significance(percentage_change)
    return {
        "absolute_change": round(absolute_change, 2),
        "percentage_change": round(percentage_change, 2),
        "severity": significance["severity"],
        "score": significance["score"]
    }


def generate_explanation(
    percentage_change: float,
    score: int,
    current_volume: float | None = None,
    average_volume: float | None = None,
    market_change: float | None = None,
    news: dict | None = None
) -> list[str]:
    explanations = []
    if abs(percentage_change) >= 1:
        direction = "rose" if percentage_change > 0 else "fell"
        explanations.append(f"Price {direction} {abs(percentage_change):.2f}%")

    if current_volume and average_volume and average_volume > 0:
        ratio = current_volume / average_volume
        if ratio >= 1.5:
            explanations.append(f"Trading volume is {ratio:.1f}× normal")

    if market_change is not None and abs(percentage_change - market_change) >= 2:
        explanations.append("Movement differs significantly from the broader market")

    if news and news.get("impact") in {"HIGH", "MEDIUM"}:
        explanations.append(
            f"News sentiment is {news['sentiment'].lower()} ({news['impact'].lower()} impact)"
        )

    return explanations or ["No unusual market activity detected"]
