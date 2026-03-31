---
name: price-signal
description: "Detects divergence between stock price behavior and fundamental expectations. Use when user asks about price action, whether stocks are acting well after earnings, early warning signals, or as part of Druckenmiller-style analysis. Triggers on: 'how is price action', 'are stocks acting well', 'any earnings divergences', 'price signal analysis', 'run price signal', '股價行為', '盈利後股價反應', '早期警告信號'."
version: "1.0.0"
author: "howard"
source_principle: "Druckenmiller (Real Vision, 2018): 'If a company was reporting great earnings and the stock just didn't act well for 3-4 months, almost inevitably something happened that you didn't foresee 6 months down the road. Price was a valuable signal.'"
caveat: "Druckenmiller also said in 2018 that algo trading has 'severely inhibited' his ability to read price signals. This skill is weighted at only 15% in conviction-synthesizer — the lowest of the four — for this reason."
outputs:
  - overall_score: "0-100 integer"
  - overall_direction: "bullish | neutral | bearish"
  - notable_divergences: "list of stocks showing earnings beat + price drop"
  - summary_json: "reports/price_signal_YYYY-MM-DD.json"
  - summary_md: "reports/price_signal_YYYY-MM-DD.md"
api_keys_required:
  - none: "Uses yfinance (free, no API key needed)"
---

# Price Signal Analyzer

## Purpose

Detect when stock price behavior diverges from fundamental expectations.
The most important signal: a stock that beats earnings estimates but
then sells off — Druckenmiller's classic early warning that something
bad is coming that analysts haven't discovered yet.

**Important caveat**: Druckenmiller explicitly acknowledged in 2018 that
algorithmic trading has reduced the reliability of this signal compared
to when he first developed it. This is why this skill carries the lowest
weight (15%) in the conviction synthesizer.

---

## What This Skill Measures

| Signal | Bullish | Bearish |
|--------|---------|---------|
| Post-earnings price reaction | Beat estimates AND stock rises | Beat estimates but stock falls |
| Price momentum vs sector | Stock leading its sector ETF | Stock lagging sector despite good news |

---

## The Classic Druckenmiller Divergence

The most actionable signal is the **bearish divergence**:

```
Company beats EPS estimates by >5%
Stock price drops >2% in the 3 days after earnings
→ Market knows something analysts don't yet
→ This is a warning to reduce or exit
```

Druckenmiller used this pattern to exit positions before bad news
became public knowledge. The stock price was telling him something
the income statement wasn't.

---

## Execution

```bash
python price-signal\scripts\price_signal.py --output-dir reports\
```

No API key required. Uses yfinance free data.
Runs in 2-3 minutes (25 stocks, earnings + price data).

---

## Sectors and Stocks Monitored

5 key sectors, 5 stocks each (25 total):

- Technology: NVDA, MSFT, AAPL, META, AMD
- Financials: JPM, GS, MS, BAC, BLK
- Healthcare: LLY, UNH, ABBV, TMO, AMGN
- Energy: XOM, CVX, COP, OXY, SLB
- Industrials: CAT, GE, RTX, HON, DE

These are the largest, most liquid names where price signal is
most meaningful and least distorted by thin trading.

---

## Output Format

### JSON

```json
{
  "skill": "price-signal",
  "version": "1.0.0",
  "date": "2026-03-31",
  "overall_score": 55.0,
  "overall_direction": "neutral",
  "implication": "Mixed price signals...",
  "notable_divergences": [
    "NVDA: beat earnings by 8.2% but stock reacted -4.1% -- warning signal"
  ],
  "sector_results": {
    "Technology": {
      "score": 50.0,
      "direction": "neutral",
      "bullish": 2,
      "bearish": 2
    }
  },
  "caveat": "Druckenmiller noted algo trading has reduced reliability..."
}
```

---

## Integration with conviction-synthesizer

```python
price = load_json("reports/price_signal_latest.json")
score      = price["overall_score"]        # 0-100
direction  = price["overall_direction"]    # bullish / neutral / bearish
divergences = price["notable_divergences"] # list, check for warnings
```

Weight in synthesizer: **15%** — lowest of four skills.

If `notable_divergences` is non-empty, synthesizer adds an additional
warning flag to the output regardless of the score.

---

## Limitations

- Earnings dates from yfinance may have 1-2 day lag
- Post-earnings price window is only 3 days — noisy
- Algo trading has reduced signal reliability (Druckenmiller's own admission)
- Best used as a confirming or warning signal, not a primary driver
