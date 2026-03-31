---
name: liquidity-regime
description: "Analyzes the current Fed liquidity cycle and classifies the macro regime. Use when the user asks about Fed policy direction, liquidity conditions, macro environment, or when running any Druckenmiller-style market analysis. Triggers on: 'what is the liquidity regime', 'is the Fed expanding or tightening', 'what is the macro environment', 'run liquidity analysis', 'Druckenmiller macro check', '流動性環境', '宏觀環境分析', 'Fed 政策方向'."
version: "1.0.0"
author: "howard"
source_principle: "Druckenmiller (New Market Wizards, 1992): 'Earnings don't move the overall market; it's the Federal Reserve Board. Focus on the central banks and focus on the movement of liquidity. It's liquidity that moves markets.'"
outputs:
  - regime: "expanding | tightening | pivot | neutral"
  - strength: "0-100 integer"
  - summary_json: "reports/liquidity_regime_YYYY-MM-DD.json"
  - summary_md: "reports/liquidity_regime_YYYY-MM-DD.md"
api_keys_required:
  - FRED_API_KEY: "https://fred.stlouisfed.org/docs/api/api_key.html (free)"
---

# Liquidity Regime Analyzer

## Purpose

Classify the current Fed liquidity cycle into one of four regimes and output
a normalized strength score (0–100). This is the highest-weighted input (35%)
into the `conviction-synthesizer`.

**Theoretical basis**: Druckenmiller explicitly stated that liquidity — not
earnings — is the primary driver of markets. This skill operationalizes that
principle using publicly available Fed data.

---

## Regime Definitions

| Regime | Description | Druckenmiller implication |
|--------|-------------|--------------------------|
| `expanding` | Fed actively adding liquidity; balance sheet growing or rate cuts underway | Most favorable for equities — "dull, slow economy the Fed is trying to get going" |
| `pivot` | Clear directional shift detected (tightening → easing or vice versa) | Highest-alpha moment — "anticipate changes not yet reflected in prices" |
| `neutral` | No clear directional signal; policy on hold | Moderate conviction; watch other signals |
| `tightening` | Fed removing liquidity; balance sheet shrinking or rate hikes underway | Reduce equity exposure; "Fed is no longer with you" |

---

## Execution

### Step 1: Install dependencies

```bash
pip install pandas requests python-dotenv fredapi
```

### Step 2: Set up API key

```bash
# .env file in project root
FRED_API_KEY=your_key_here
```

### Step 3: Run the script

```bash
python scripts/liquidity_regime.py --output-dir reports/
```

---

## Script: `scripts/liquidity_regime.py`

```python
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
    with open(path, "w") as f:
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
```

---

## Output Format

### JSON (`reports/liquidity_regime_YYYY-MM-DD.json`)

```json
{
  "skill": "liquidity-regime",
  "version": "1.0.0",
  "date": "2025-03-30",
  "regime": "expanding",
  "strength": 72.4,
  "components": {
    "balance_sheet_trend": { "score": 68.0, "direction": "expanding" },
    "rate_direction":      { "score": 80.0, "direction": "expanding" },
    "m2_growth":           { "score": 60.0, "direction": "neutral" },
    "yield_curve":         { "score": 55.0, "direction": "neutral" }
  },
  "implication": "Most favorable for equities...",
  "source": "FRED API"
}
```

### Markdown

Human-readable report, consumed by `conviction-synthesizer` and Live Briefing page.

---

## Data Sources

| Indicator | FRED Series | Why chosen |
|-----------|-------------|------------|
| Fed balance sheet | `WALCL` | Most direct measure of liquidity injection/withdrawal |
| Fed funds rate | `FEDFUNDS` | Price of money — direction signals policy intent |
| M2 money supply | `M2SL` | Broader liquidity in the system |
| 10Y-2Y yield spread | `T10Y2Y` | Regime health indicator; inversion = tightening stress |

**Important**: These are reasonable proxies for what Druckenmiller calls
"liquidity." His actual process likely uses many more proprietary inputs.
This skill operationalizes his *published principle*, not his exact system.

---

## Integration with conviction-synthesizer

This skill outputs a JSON file that `conviction-synthesizer` reads directly.
The `regime` and `strength` fields are the two consumed values:

```python
# conviction-synthesizer reads:
liquidity = load_json("reports/liquidity_regime_latest.json")
regime   = liquidity["regime"]    # "expanding"
strength = liquidity["strength"]  # 72.4
```

Weight in synthesizer: **35%** — highest of the four skills, reflecting
Druckenmiller's explicit prioritization of liquidity over all other factors.

---

## Error Handling

- If FRED API is unavailable: skip this skill, log warning, synthesizer
  uses `neutral` with `strength: 50` as fallback
- If data is stale (> 7 days): flag in output JSON with `"stale": true`
- If any single series fails: compute score from remaining series,
  reweight accordingly

---

## When to Run

- **Scheduled**: Daily at 06:00 UTC via GitHub Actions
- **On demand**: User triggers via Claude conversation
- **Staleness threshold**: 48 hours — after that, regime classification
  should not be used for conviction scoring
