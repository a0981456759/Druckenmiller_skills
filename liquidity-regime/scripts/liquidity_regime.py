"""
liquidity_regime.py
Fetches 4 FRED series, computes regime and strength score.
Outputs JSON + Markdown report.
"""

import os, json, argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fredapi import Fred
import pandas as pd

load_dotenv()

SERIES = {
    "fed_assets":    "WALCL",    # Fed total assets (balance sheet)
    "fed_funds":     "FEDFUNDS", # Effective Fed funds rate
    "m2":            "M2SL",     # M2 money supply
    "yield_spread":  "T10Y2Y",   # 10Y-2Y Treasury spread
}

WEIGHTS = {
    "balance_sheet_trend": 0.35,
    "rate_direction":      0.30,
    "m2_growth":           0.20,
    "yield_curve":         0.15,
}

def fetch_series(fred: Fred, series_id: str, periods: int = 24) -> pd.Series:
    end = datetime.today()
    start = end - timedelta(days=periods * 35)
    data = fred.get_series(series_id, start, end)
    return data.dropna()

def score_balance_sheet(series: pd.Series) -> tuple[float, str]:
    """3-month trend of Fed balance sheet. Expanding = bullish."""
    if len(series) < 2:
        return 50.0, "neutral"
    recent = series.iloc[-1]
    prior  = series.iloc[-13] if len(series) >= 13 else series.iloc[0]
    pct_change = (recent - prior) / prior * 100
    if pct_change > 2:
        return min(100, 50 + pct_change * 5), "expanding"
    elif pct_change < -2:
        return max(0, 50 + pct_change * 5), "tightening"
    return 50.0, "neutral"

def score_rate_direction(series: pd.Series) -> tuple[float, str]:
    """Direction of Fed funds rate over last 6 months."""
    if len(series) < 6:
        return 50.0, "neutral"
    recent = series.iloc[-1]
    prior  = series.iloc[-6]
    delta  = recent - prior
    if delta < -0.25:
        score = min(100, 50 + abs(delta) * 20)
        return score, "expanding"
    elif delta > 0.25:
        score = max(0, 50 - delta * 20)
        return score, "tightening"
    return 50.0, "neutral"

def score_m2(series: pd.Series) -> tuple[float, str]:
    """YoY M2 growth rate."""
    if len(series) < 12:
        return 50.0, "neutral"
    recent = series.iloc[-1]
    year_ago = series.iloc[-12]
    yoy = (recent - year_ago) / year_ago * 100
    if yoy > 4:
        return min(100, 50 + yoy * 3), "expanding"
    elif yoy < 0:
        return max(0, 50 + yoy * 3), "tightening"
    return 50.0, "neutral"

def score_yield_curve(series: pd.Series) -> tuple[float, str]:
    """10Y-2Y spread. Steepening = more liquidity-friendly."""
    if len(series) < 2:
        return 50.0, "neutral"
    current = series.iloc[-1]
    prior   = series.iloc[-3] if len(series) >= 3 else series.iloc[0]
    if current > 0 and current > prior:
        return min(100, 50 + current * 15), "expanding"
    elif current < -0.5:
        return max(0, 50 + current * 15), "tightening"
    return 50.0, "neutral"

def classify_regime(scores: dict) -> tuple[str, float]:
    """Weighted average → regime classification."""
    weighted = sum(
        scores[k]["score"] * WEIGHTS[k] for k in WEIGHTS
    )
    # Detect pivot: any component flipped direction in last 3 months
    directions = [scores[k]["direction"] for k in scores]
    expanding_count = directions.count("expanding")
    tightening_count = directions.count("tightening")
    if expanding_count >= 2 and tightening_count >= 1:
        return "pivot", round(weighted, 1)
    if weighted >= 65:
        return "expanding", round(weighted, 1)
    elif weighted <= 35:
        return "tightening", round(weighted, 1)
    return "neutral", round(weighted, 1)

def build_report(regime: str, strength: float, scores: dict, date: str) -> dict:
    implication = {
        "expanding":  "Most favorable for equities. Druckenmiller: 'best environment is a dull economy the Fed is trying to get going.'",
        "pivot":      "Highest-alpha moment. Anticipate the shift before consensus. Watch for sector rotation.",
        "neutral":    "Mixed signals. Preserve capital. Wait for clearer regime.",
        "tightening": "Reduce equity exposure. Fed removing liquidity. 'Fed is no longer with you.'",
    }
    return {
        "skill":       "liquidity-regime",
        "version":     "1.0.0",
        "date":        date,
        "regime":      regime,
        "strength":    strength,
        "components":  scores,
        "implication": implication[regime],
        "source":      "FRED API",
    }

def write_markdown(report: dict, path: str):
    lines = [
        f"# Liquidity Regime — {report['date']}",
        f"",
        f"**Regime**: `{report['regime'].upper()}`  ",
        f"**Strength**: {report['strength']} / 100",
        f"",
        f"## Implication",
        f"{report['implication']}",
        f"",
        f"## Component Scores",
        f"| Component | Score | Direction |",
        f"|-----------|-------|-----------|",
    ]
    for k, v in report["components"].items():
        lines.append(f"| {k} | {v['score']:.1f} | {v['direction']} |")
    lines += [
        f"",
        f"## Druckenmiller Principle",
        f"> 'Earnings don't move the overall market; it's the Federal Reserve Board.",
        f"> Focus on the central banks and focus on the movement of liquidity.'",
        f"",
        f"*Source: FRED API. Generated by liquidity-regime skill v1.0.0*",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reports/")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    fred = Fred(api_key=os.getenv("FRED_API_KEY"))
    date = datetime.today().strftime("%Y-%m-%d")

    print("Fetching FRED data...")
    data = {k: fetch_series(fred, v) for k, v in SERIES.items()}

    scores = {
        "balance_sheet_trend": dict(zip(["score", "direction"], score_balance_sheet(data["fed_assets"]))),
        "rate_direction":      dict(zip(["score", "direction"], score_rate_direction(data["fed_funds"]))),
        "m2_growth":           dict(zip(["score", "direction"], score_m2(data["m2"]))),
        "yield_curve":         dict(zip(["score", "direction"], score_yield_curve(data["yield_spread"]))),
    }

    regime, strength = classify_regime(scores)
    report = build_report(regime, strength, scores, date)

    json_path = os.path.join(args.output_dir, f"liquidity_regime_{date}.json")
    md_path   = os.path.join(args.output_dir, f"liquidity_regime_{date}.md")

    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    write_markdown(report, md_path)

    print(f"Regime: {regime.upper()} | Strength: {strength}/100")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")

if __name__ == "__main__":
    main()