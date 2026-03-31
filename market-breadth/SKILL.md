---
name: market-breadth
description: "Analyzes stock market participation breadth and detects blow-off risk. Use when user asks about market health, breadth, whether gains are broad-based or concentrated, market top risk, or as part of Druckenmiller-style analysis. Triggers on: 'how is market breadth', 'are gains broad-based', 'is the market healthy', 'blow-off risk', 'run breadth analysis', 'market concentration', '市場廣度', '漲勢是否健康', '吹頂風險', '板塊輪動'."
version: "1.0.0"
author: "howard"
source_principle: "Druckenmiller (New Market Wizards, 1987 crash call): 'My technical analysis showed that the breadth wasn't there -- the market's strength was primarily concentrated in the high capitalization stocks, with the broad spectrum of issues lagging well behind. This factor made the rally look like a blow-off.'"
outputs:
  - composite_score: "0-100 integer"
  - health: "healthy | neutral | deteriorating"
  - blow_off_risk: "boolean"
  - summary_json: "reports/market_breadth_YYYY-MM-DD.json"
  - summary_md: "reports/market_breadth_YYYY-MM-DD.md"
api_keys_required:
  - FRED_API_KEY: "https://fred.stlouisfed.org/docs/api/api_key.html (free)"
---

# Market Breadth Analyzer

## Purpose

Measure whether market gains are broad-based (healthy) or concentrated
in a handful of large-cap stocks (blow-off risk). This is the third input
(25% weight) into `conviction-synthesizer`.

**Theoretical basis**: Druckenmiller's 1987 top call was based entirely
on breadth divergence — the index was rising but the majority of stocks
were not participating. He identified this as the defining signal of an
unsustainable rally.

---

## What This Skill Measures

| Signal | What it detects | Weight |
|--------|----------------|--------|
| Equal-weight vs cap-weight divergence | Mega-cap concentration vs broad participation | 40% |
| NYSE Advance/Decline line | How many stocks actually rising vs falling | 40% |
| New 52-week highs vs lows | Internal market strength | 20% |

The blow-off detector fires when the index is rising but all three
breadth signals are deteriorating simultaneously — Druckenmiller's
exact 1987 pattern.

---

## Execution

### Step 1: Dependencies (already installed from liquidity-regime)

```bash
conda activate druck
# fredapi already installed
```

### Step 2: Run

```bash
cd druckenmiller-skills
python market-breadth\scripts\market_breadth.py --output-dir reports\
```

---

## FRED Series Used

| Series | FRED ID | Description |
|--------|---------|-------------|
| S&P 500 (cap-weight) | `SP500` | Benchmark index |
| S&P 500 Equal-weight | `SPXEW` | Same stocks, equal weight |
| NYSE Advancing issues | `UPADNS` | Daily advancing stocks |
| NYSE Declining issues | `DOWADNS` | Daily declining stocks |
| NYSE New 52W highs | `HHNHBSL` | New high count |
| NYSE New 52W lows | `LOLNBSL` | New low count |

All free via FRED API.

---

## Health Classification

| Score | Health | Druckenmiller implication |
|-------|--------|--------------------------|
| 65-100 | `healthy` | Broad participation. Breadth confirms rally. Add conviction. |
| 41-64 | `neutral` | Mixed signals. Use liquidity and earnings as primary drivers. |
| 0-40 | `deteriorating` | Concentration risk. Reduce exposure or hedge. |

**Blow-off flag** triggers independently when index is up 5%+ over 3 months
but breadth signals are all deteriorating. This is the highest-priority
warning in the entire skill system.

---

## Blow-off Detection Logic

```
IF index_3m_return > 5% AND any of:
  - equal-weight lagging cap-weight by > 2%
  - A/D line trending down
  - new highs collapsing
THEN blow_off_risk = True
```

When blow-off risk is True, `conviction-synthesizer` applies a hard cap
of 40 on the overall conviction score regardless of other signals.

---

## Output Format

### JSON

```json
{
  "skill": "market-breadth",
  "version": "1.0.0",
  "date": "2026-03-31",
  "composite_score": 58.3,
  "health": "neutral",
  "blow_off_risk": false,
  "blow_off_warning": "",
  "implication": "Mixed breadth signals...",
  "components": {
    "ew_vs_cw": {
      "score": 45.0,
      "direction": "concentrated",
      "ew_3m_pct": 4.2,
      "cw_3m_pct": 8.1,
      "divergence": -3.9
    },
    "advance_decline": {
      "score": 63.0,
      "direction": "neutral",
      "ad_ratio_now": 0.523,
      "ad_ratio_prior": 0.501,
      "ad_trend": 0.022
    },
    "highs_lows": {
      "score": 61.0,
      "direction": "neutral",
      "hl_ratio": 0.61,
      "hl_trend": 0.012
    }
  }
}
```

---

## Integration with conviction-synthesizer

```python
breadth = load_json("reports/market_breadth_latest.json")
score      = breadth["composite_score"]   # 0-100
health     = breadth["health"]            # healthy/neutral/deteriorating
blow_off   = breadth["blow_off_risk"]     # True/False
```

Weight in synthesizer: **25%**

If `blow_off_risk` is True: synthesizer caps overall conviction at 40.

---

## When to Run

- **Scheduled**: Daily at 06:30 UTC via GitHub Actions (after liquidity-regime)
- **On demand**: User triggers via Claude conversation
- **Staleness threshold**: 48 hours
