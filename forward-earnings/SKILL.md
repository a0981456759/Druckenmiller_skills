---
name: forward-earnings
description: "Analyzes forward EPS revision direction and analyst consensus momentum across S&P 500 sectors. Use when user asks about earnings outlook, analyst revisions, sector momentum, or as part of Druckenmiller-style analysis. Triggers on: 'what are forward earnings doing', 'which sectors have earnings momentum', 'analyst revisions', 'run forward earnings analysis', 'earnings expectations', '盈利預期', '分析師修正方向', '板塊盈利動能', '前瞻盈利'."
version: "2.0.0"
author: "howard"
source_principle: "Druckenmiller (New Market Wizards, 1992): 'What a company's been earning doesn't mean anything. What you have to look at is what people think it's going to earn. If you can see something in two years is going to be entirely different than the conventional wisdom, that's how you make money.'"
outputs:
  - overall_score: "0-100 integer"
  - overall_direction: "beat | miss | neutral"
  - sector_ranking: "list of sectors sorted by forward EPS momentum"
  - summary_json: "reports/forward_earnings_YYYY-MM-DD.json"
  - summary_md: "reports/forward_earnings_YYYY-MM-DD.md"
api_keys_required: []
data_source: "Yahoo Finance via yfinance (free, no API key required)"
---

# Forward Earnings Analyzer

## Purpose

Track whether analyst consensus EPS estimates are being revised up or down
across S&P 500 sectors. Uses genuinely forward-looking analyst data, not
historical actuals. This is the second input (25% weight) into
`conviction-synthesizer`.

**Theoretical basis**: Druckenmiller explicitly said current earnings are
irrelevant -- what matters is the *direction* consensus is moving over the
next 18-24 months. Rising EPS revisions = market hasn't fully priced the
move yet = opportunity.

---

## What This Skill Measures

| Signal | Source | What it captures |
|--------|--------|-----------------|
| EPS revisions (30d) | `yf.Ticker.eps_revisions` | Net analysts upgrading vs downgrading in last 30 days |
| EPS trend vs 30d ago | `yf.Ticker.eps_trend` | Direction consensus is moving |
| Next-year growth estimate | `yf.Ticker.growth_estimates` | Analyst forecast for next FY |

All three are forward-looking. No historical EPS used.
Coverage: 9 GICS sectors x 10 representative large-caps = 90 stocks.

---

## Execution

### Step 1: Install yfinance (one time)

```bash
conda activate druck
pip install yfinance
```

### Step 2: Run

```bash
cd druckenmiller-skills
python forward-earnings\scripts\forward_earnings.py --output-dir reports\
```

Runtime: ~4-5 minutes (90 stocks x 0.3s delay).

---

## Scoring Logic

For each ticker:
  revision_score = (up_30d - down_30d) / (up_30d + down_30d)
  trend_score    = (current_eps - eps_30d_ago) / eps_30d_ago
  composite      = revision_score * 0.5 + trend_score * 0.3 + growth_contribution * 0.2
  direction      = "up" if composite > 0.15 else "down" if < -0.15 else "neutral"

For each sector:
  breadth_score  = 50 + (up_count - down_count) / total * 40
  sector_score   = breadth * 0.5 + revision * 0.3 + growth * 0.2

---

## Direction Classification

| Direction | Condition | Implication |
|-----------|-----------|-------------|
| `beat` | 6+ sectors = "up" | Consensus underestimating -- opportunity |
| `miss` | 6+ sectors = "down" | Consensus too optimistic -- risk |
| `neutral` | Mixed | Use other signals as primary |

---

## Known Limitations

- yfinance reflects Yahoo Finance consensus, not Bloomberg/FactSet
- Growth estimates > 200% are capped to prevent distortion from negative base EPS
- Delisted tickers (e.g. PXD) return warnings but do not break the run

---

## Integration with conviction-synthesizer

```python
fwd = load_json("reports/forward_earnings_latest.json")
score      = fwd["overall_score"]        # 0-100
direction  = fwd["overall_direction"]    # beat / miss / neutral
top_sector = fwd["sector_ranking"][0]["sector"]
```

Weight in synthesizer: 25%
