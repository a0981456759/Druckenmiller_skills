"""
forward_earnings.py v2.0
Uses yfinance analyst estimates — genuinely forward-looking data.

Key signals (all free, no API key needed):
  eps_revisions:    analysts revised EPS up/down in last 7/30/60/90 days
  eps_trend:        current consensus EPS vs 30 days ago
  growth_estimates: next-year growth rate forecast

Why this is correct for Druckenmiller:
  "What you have to look at is what people THINK it's going to earn."
  eps_revisions and eps_trend are exactly that.
"""

import os, json, argparse, time
from datetime import datetime
from dotenv import load_dotenv
import yfinance as yf
import pandas as pd

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

SECTOR_STOCKS = {
    "Technology":        ["AAPL", "MSFT", "NVDA", "AVGO", "META",
                          "AMD",  "ORCL", "CRM",  "QCOM", "AMAT"],
    "Financials":        ["JPM",  "BAC",  "WFC",  "GS",   "MS",
                          "BLK",  "C",    "AXP",  "SCHW", "USB"],
    "Healthcare":        ["UNH",  "JNJ",  "LLY",  "ABBV", "MRK",
                          "TMO",  "ABT",  "DHR",  "AMGN", "BMY"],
    "Energy":            ["XOM",  "CVX",  "COP",  "SLB",  "EOG",
                          "OXY",   "MPC",  "PSX",  "VLO",  "HAL"],
    "Industrials":       ["CAT",  "HON",  "UPS",  "BA",   "GE",
                          "RTX",  "LMT",  "DE",   "MMM",  "FDX"],
    "Consumer Discret.": ["AMZN", "TSLA", "HD",   "MCD",  "NKE",
                          "LOW",  "SBUX", "TJX",  "BKNG", "GM"],
    "Consumer Staples":  ["PG",   "KO",   "PEP",  "WMT",  "COST",
                          "PM",   "MO",   "MDLZ", "CL",   "GIS"],
    "Materials":         ["LIN",  "APD",  "SHW",  "FCX",  "NEM",
                          "ECL",  "DD",   "ALB",  "VMC",  "MLM"],
    "Utilities":         ["NEE",  "DUK",  "SO",   "D",    "AEP",
                          "EXC",  "XEL",  "WEC",  "ES",   "ETR"],
}


def safe_float(val, default=0.0):
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def get_ticker_forward_signal(ticker: str) -> dict:
    """
    Pull forward-looking analyst data for one ticker via yfinance.

    Signals used:
      revision_score  : net EPS revisions in last 30 days (-1 to +1)
      trend_score     : EPS consensus change vs 30 days ago (-1 to +1)
      next_year_growth: analyst next-FY growth forecast (%)
      direction       : up | down | neutral
    """
    empty = {"direction": "neutral", "composite": 0.0,
             "revision_score": 0.0, "trend_score": 0.0, "next_year_growth": 0.0}
    try:
        t = yf.Ticker(ticker)

        # 1. EPS Revisions — up/down counts in last 30 days
        revision_score = 0.0
        revisions = t.eps_revisions
        if revisions is not None and not revisions.empty:
            for label in ["Next Year", "Current Year"]:
                if label in revisions.index:
                    row = revisions.loc[label]
                    up   = safe_float(row.get("upLast30days",   row.get("Up Last 30 Days")))
                    down = safe_float(row.get("downLast30days", row.get("Down Last 30 Days")))
                    total = up + down
                    if total > 0:
                        revision_score = (up - down) / total
                    break

        # 2. EPS Trend — current consensus vs 30 days ago
        trend_score = 0.0
        trend = t.eps_trend
        if trend is not None and not trend.empty:
            for label in ["Next Year", "Current Year"]:
                if label in trend.index:
                    row     = trend.loc[label]
                    current = safe_float(row.get("current",   row.get("Current")))
                    ago_30  = safe_float(row.get("30daysAgo", row.get("30 Days Ago")))
                    if ago_30 != 0:
                        pct = (current - ago_30) / abs(ago_30)
                        trend_score = max(-1.0, min(1.0, pct * 10))
                    break

        # 3. Next-year growth estimate
        next_year_growth = 0.0
        growth = t.growth_estimates
        if growth is not None and not growth.empty:
            for label in ["Next Year", "+1y"]:
                if label in growth.index:
                    val = growth.loc[label]
                    if hasattr(val, "iloc"):
                        val = val.iloc[0]
                    next_year_growth = safe_float(val) * 100
                    break
        if abs(next_year_growth) > 200:
            next_year_growth = 0.0
        # Composite signal
        growth_contribution = (
            0.2  if next_year_growth > 10 else
            -0.2 if next_year_growth < 0  else 0.0
        )
        composite = revision_score * 0.5 + trend_score * 0.3 + growth_contribution

        direction = (
            "up"   if composite >  0.15 else
            "down" if composite < -0.15 else
            "neutral"
        )

        return {
            "direction":        direction,
            "composite":        round(composite, 3),
            "revision_score":   round(revision_score, 3),
            "trend_score":      round(trend_score, 3),
            "next_year_growth": round(next_year_growth, 1),
        }

    except Exception as e:
        print(f"    Warning: {ticker} -- {e}")
        return empty


def analyze_sector(sector: str, tickers: list) -> dict:
    results = []
    for ticker in tickers:
        results.append(get_ticker_forward_signal(ticker))
        time.sleep(0.3)

    up_count   = sum(1 for r in results if r["direction"] == "up")
    down_count = sum(1 for r in results if r["direction"] == "down")
    breadth    = (up_count - down_count) / len(tickers)

    avg_revision       = sum(r["revision_score"]   for r in results) / len(results)
    avg_next_yr_growth = sum(r["next_year_growth"] for r in results) / len(results)

    breadth_score  = 50 + breadth       * 40
    revision_score = 50 + avg_revision  * 40
    growth_score   = min(100, max(0, 50 + avg_next_yr_growth * 2))

    score = breadth_score * 0.5 + revision_score * 0.3 + growth_score * 0.2
    score = max(0.0, min(100.0, score))

    return {
        "score":              round(score, 1),
        "direction":          "up" if breadth > 0.2 else "down" if breadth < -0.2 else "neutral",
        "up_revised":         up_count,
        "down_revised":       down_count,
        "avg_revision_score": round(avg_revision, 3),
        "avg_next_yr_growth": round(avg_next_yr_growth, 1),
    }


def compute_overall(sector_results: dict) -> tuple[float, str]:
    scores    = [v["score"]     for v in sector_results.values()]
    up_sects  = sum(1 for v in sector_results.values() if v["direction"] == "up")
    dn_sects  = sum(1 for v in sector_results.values() if v["direction"] == "down")
    overall   = sum(scores) / len(scores)
    direction = "beat" if up_sects >= 6 else "miss" if dn_sects >= 6 else "neutral"
    return round(overall, 1), direction


def build_report(overall_score, overall_direction, sector_results, date):
    implication = {
        "beat": (
            "Analysts broadly revising EPS estimates upward. Consensus becoming more "
            "optimistic -- the setup Druckenmiller calls 'how you make money': "
            "seeing what conventional wisdom has not yet priced in."
        ),
        "miss": (
            "Analysts cutting EPS estimates across sectors. Forward expectations "
            "deteriorating. Reduce exposure; wait for revision cycle to stabilize."
        ),
        "neutral": (
            "Mixed revision picture. No broad directional edge from forward earnings. "
            "Weight liquidity regime and breadth signals more heavily."
        ),
    }
    ranked = sorted(
        [{"sector": k, **v} for k, v in sector_results.items()],
        key=lambda x: x["score"], reverse=True
    )
    return {
        "skill":             "forward-earnings",
        "version":           "2.0.0",
        "date":              date,
        "overall_score":     overall_score,
        "overall_direction": overall_direction,
        "implication":       implication[overall_direction],
        "sector_results":    sector_results,
        "sector_ranking":    ranked,
        "methodology":       "Analyst EPS revisions (30d) + EPS trend vs 30d ago + next-year growth estimate",
        "source":            "Yahoo Finance via yfinance (free)",
    }


def write_markdown(report: dict, path: str):
    ranked = report["sector_ranking"]
    lines = [
        f"# Forward Earnings Analysis -- {report['date']}",
        "",
        f"**Overall**: `{report['overall_direction'].upper()}`",
        f"**Score**: {report['overall_score']} / 100",
        "",
        "## Implication",
        report["implication"],
        "",
        "## Methodology",
        report["methodology"],
        "",
        "## Sector Ranking (forward EPS revision momentum)",
        "| Rank | Sector | Score | Direction | Up revised | Next-yr growth |",
        "|------|--------|-------|-----------|------------|----------------|",
    ]
    for i, s in enumerate(ranked, 1):
        lines.append(
            f"| {i} | {s['sector']} | {s['score']} | {s['direction']} "
            f"| {s['up_revised']}/{s['up_revised']+s['down_revised']} "
            f"| {s['avg_next_yr_growth']:+.1f}% |"
        )
    lines += [
        "",
        "## Druckenmiller Principle",
        "> \"What a company's been earning doesn't mean anything.",
        "> What you have to look at is what people think it's going to earn.",
        "> If you can see something in two years is going to be entirely",
        "> different than the conventional wisdom, that's how you make money.\"",
        "",
        f"*Source: Yahoo Finance (yfinance). Generated by forward-earnings v2.0.0*",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reports/")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    date = datetime.today().strftime("%Y-%m-%d")

    print("Analyzing forward earnings (yfinance analyst estimates)...")
    sector_results = {}
    for sector, tickers in SECTOR_STOCKS.items():
        print(f"  {sector}...")
        sector_results[sector] = analyze_sector(sector, tickers)

    overall_score, overall_direction = compute_overall(sector_results)
    report = build_report(overall_score, overall_direction, sector_results, date)
    ranked = report["sector_ranking"]

    json_path = os.path.join(args.output_dir, f"forward_earnings_{date}.json")
    md_path   = os.path.join(args.output_dir, f"forward_earnings_{date}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    write_markdown(report, md_path)

    print(f"\nOverall: {overall_direction.upper()} | Score: {overall_score}/100")
    print(f"Top sector:    {ranked[0]['sector']} ({ranked[0]['score']})")
    print(f"Bottom sector: {ranked[-1]['sector']} ({ranked[-1]['score']})")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()