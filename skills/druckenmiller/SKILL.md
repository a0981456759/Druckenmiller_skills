---
name: druckenmiller
description: Use this skill when the user asks about today's market, conviction level, position sizing, or any question about what Druckenmiller's framework says about current conditions. Trigger phrases include "今天市場", "確信度", "今日判斷", "該持多少倉位", "Druckenmiller 怎麼看", "conviction score", "market conviction", "position sizing today".
version: 1.0.0
---

# Druckenmiller Conviction Skill

## Step 1 — Fetch today's data

Compute today's date (YYYY-MM-DD) and fetch:

```
https://druckenmiller-skills.vercel.app/reports/conviction_YYYY-MM-DD.json
```

Replace `VERCEL_URL` with the actual deployment domain.

If fetch fails: tell the user "今日數據尚未生成，pipeline 可能尚未執行。"

## Step 2 — Parse the JSON

Key fields:

| Field | Meaning |
|---|---|
| `conviction_score` | 0–100 overall score |
| `conviction_zone` | fat pitch / high conviction / moderate / low conviction / capital preservation |
| `equity_range` | recommended equity allocation |
| `action` | plain-language recommendation (Chinese) |
| `blow_off_risk` | true = reduce position ceiling to 50% |
| `notable_divergences` | stocks that beat earnings but sold off — 6-month warning signal |
| `components` | 4 signals with individual scores + directions |

## Step 3 — Interpret signals

### Liquidity (weight 35%) — always lead with this
> "It's liquidity that moves markets, not earnings." — Druckenmiller

- `expanding` / `pivot` → strongest bullish signal
- `tightening` → biggest headwind, override positive fundamentals
- `neutral` → wait for confirmation

### Forward Earnings (weight 25%)
- `beat` → analysts upgrading, "conventional wisdom hasn't priced it in yet"
- `miss` → deteriorating expectations

### Market Breadth (weight 25%)
- `healthy` → broad participation, gains not concentrated in mega-caps
- `deteriorating` → like 1987 top — strength only in large caps, dangerous
- `blow_off_risk: true` → Druckenmiller's retreat signal

### Price Signal (weight 15%)
- `notable_divergences` non-empty → "almost certainly a bad news preview 6 months out"
- List each diverging stock explicitly

## Step 4 — Score → position mapping

| Score | Zone | Equity | Action |
|---|---|---|---|
| 85–100 | fat pitch | 90–100% | 全力押注 — once or twice a year |
| 70–84 | high conviction | 70–89% | 積極加碼 |
| 50–69 | moderate | 50–69% | 標準倉位，等催化劑 |
| 30–49 | low conviction | 20–49% | 縮倉，cash is a position |
| 0–29 | capital preservation | 0–19% | 最大防禦 |

## Step 5 — Response format

1. **Lead with the score and zone** — one sentence
2. **Action recommendation** — direct, no hedging
3. **Signal breakdown** — lead with liquidity, then the others
4. **Divergence warning** — if any, name the stocks
5. **Close with the Druckenmiller quote** from the JSON

Keep it concise. Druckenmiller doesn't equivocate — neither should you.
End with: *（數據來源：Yahoo Finance / FRED / FMP。僅供研究，非投資建議。）*
