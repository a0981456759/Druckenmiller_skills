# Druckenmiller Conviction Skill

A Claude Code skill that channels Stanley Druckenmiller's investment framework — liquidity-first analysis, conviction scoring, and position sizing, delivered in his voice.

Every day the pipeline runs 4 signals (Liquidity, Forward Earnings, Market Breadth, Price Signal) and produces a conviction JSON. The skill reads that JSON and responds like Druckenmiller.

---

## Quick Start — Path A (Use Shared Data, 2 minutes)

You use the live data endpoint. No API keys needed, no pipeline to run.

**1. Install the skill**

```bash
claude skill install https://github.com/a0981456759/druckenmiller-skill
```

Or manually: copy `skills/druckenmiller/SKILL.md` and `skills/druckenmiller/PERSONA.md` into your Claude Code skills folder.

**2. Ask Claude**

```
今天市場怎樣？
Druckenmiller 今天怎麼看？
現在該持多少倉位？
```

That's it. The skill fetches from `https://druckenmiller-skills.vercel.app` automatically.

> Data is updated once per weekday via the pipeline. If today's report isn't ready yet, the skill will tell you.

---

## Self-Hosting — Path B (Run Your Own Pipeline)

Fork the repo and run your own data pipeline. Full control over data freshness and API usage.

### Prerequisites

- Python 3.10+
- [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html) (free)
- [FMP API key](https://financialmodelingprep.com/developer/docs) (free tier works)
- Vercel account (free)

### Setup

**1. Fork this repo**

**2. Add API keys as GitHub Secrets**

In your fork: `Settings → Secrets and variables → Actions`

| Secret | Value |
|--------|-------|
| `FRED_API_KEY` | Your FRED key |
| `FMP_API_KEY` | Your FMP key |

**3. Deploy to Vercel**

Connect your forked repo to Vercel. The `public/` folder is the static site root — Vercel will serve `public/reports/` automatically.

**4. Update the skill URL**

In `skills/druckenmiller/SKILL.md`, replace:
```
https://druckenmiller-skills.vercel.app
```
with your own Vercel deployment URL.

**5. Run the pipeline**

Trigger manually from GitHub Actions (`Actions → Daily Conviction Pipeline → Run workflow`), or run locally:

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys

python liquidity-regime/scripts/liquidity_regime.py --output-dir public/reports/
python forward-earnings/scripts/forward_earnings.py --output-dir public/reports/
python market-breadth/scripts/market_breadth.py --output-dir public/reports/
python price-signal/scripts/price_signal.py --output-dir public/reports/
python conviction-synthesizer/scripts/conviction_synthesizer.py --reports-dir public/reports/ --output-dir public/reports/
```

> **Note:** GitHub Actions IP is blocked by Yahoo Finance. Run the pipeline locally or on a VPS, then push the reports.

---

## How It Works

```
Pipeline (Python)
  ├── liquidity-regime/     → FRED + FMP data → liquidity score
  ├── forward-earnings/     → FMP earnings data → analyst revision trend
  ├── market-breadth/       → breadth indicators → participation health
  ├── price-signal/         → earnings vs. price reaction → divergence detection
  └── conviction-synthesizer/ → weighted score → conviction_YYYY-MM-DD.json

Vercel
  └── public/reports/conviction_YYYY-MM-DD.json  (static file hosting)

Claude Code Skill
  ├── skills/druckenmiller/SKILL.md   → fetches JSON, interprets signals
  └── skills/druckenmiller/PERSONA.md → Druckenmiller's voice and decision logic
```

### Conviction Score → Position

| Score | Zone | Equity Allocation |
|-------|------|------------------|
| 85–100 | Fat Pitch | 90–100% — swing hard |
| 70–84 | High Conviction | 70–89% — add aggressively |
| 50–69 | Moderate | 50–69% — hold, wait for catalyst |
| 30–49 | Low Conviction | 20–49% — reduce, cash is a position |
| 0–29 | Capital Preservation | 0–19% — maximum defense |

---

## Signal Weights

| Signal | Weight | Druckenmiller's Take |
|--------|--------|----------------------|
| Liquidity Regime | 35% | "It's liquidity that moves markets, not earnings." |
| Forward Earnings | 25% | Analyst revisions reflect what consensus hasn't priced in yet |
| Market Breadth | 25% | Broad participation = healthy; mega-cap only = 1987 warning |
| Price Signal | 15% | Stock beats earnings but drops = bad news preview 6 months out |

---

## Other Languages

- [繁體中文](README_ZH-TW.md)
- [简体中文](README_ZH-CN.md)

---

## License

MIT — use freely, attribution appreciated.

*Data sources: Yahoo Finance, FRED, Financial Modeling Prep. For research only, not investment advice.*
