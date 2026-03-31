"""
market_breadth.py v1.1.0
Measures market participation breadth.

Data sources:
  - yfinance: S&P 500 (^GSPC), Equal-weight ETF (RSP), sector ETFs
  - FRED: SP500 cap-weight for comparison

Druckenmiller (New Market Wizards, 1987 top call):
  "My technical analysis showed that the breadth wasn't there --
   the market's strength was primarily concentrated in the high
   capitalization stocks, with the broad spectrum of issues lagging
   well behind. This factor made the rally look like a blow-off."
"""

import os, json, argparse, time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf
import pandas as pd
import requests

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Tickers for breadth analysis
SP500_CW  = "^GSPC"   # S&P 500 cap-weighted
SP500_EW  = "RSP"     # Invesco S&P 500 Equal Weight ETF
RUSSELL   = "IWM"     # Russell 2000 (small caps) — if lagging = concentration risk
NASDAQ    = "^IXIC"   # Nasdaq composite

# Sector ETFs — compare best vs worst to measure rotation breadth
SECTOR_ETFS = {
    "Technology":   "XLK",
    "Financials":   "XLF",
    "Healthcare":   "XLV",
    "Energy":       "XLE",
    "Industrials":  "XLI",
    "Consumer Dis": "XLY",
    "Staples":      "XLP",
    "Materials":    "XLB",
    "Utilities":    "XLU",
}

LOOKBACK_DAYS = 90  # 3 months


def fetch_returns(ticker: str, days: int = LOOKBACK_DAYS) -> float | None:
    """Fetch price return % over last N days."""
    try:
        end   = datetime.today()
        start = end - timedelta(days=days + 10)  # buffer for weekends
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True, session=_SESSION)
        if df.empty or len(df) < 10:
            return None
        close = df["Close"].dropna()
        ret = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
        time.sleep(1.5)
        return round(float(ret.iloc[0]) if hasattr(ret, 'iloc') else float(ret), 2)
    except Exception as e:
        print(f"  Warning: {ticker} -- {e}")
        time.sleep(1.5)
        return None


def fetch_prices(ticker: str, days: int = LOOKBACK_DAYS) -> pd.Series:
    """Fetch price series."""
    try:
        end   = datetime.today()
        start = end - timedelta(days=days + 10)
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True, session=_SESSION)
        if df.empty:
            return pd.Series(dtype=float)
        time.sleep(1.5)
        return df["Close"].dropna()
    except Exception as e:
        print(f"  Warning: {ticker} -- {e}")
        time.sleep(1.5)
        return pd.Series(dtype=float)


# ── Signal 1: Equal-weight vs Cap-weight ─────────────────────────────────────

def score_ew_vs_cw() -> dict:
    """
    RSP (equal-weight) vs ^GSPC (cap-weight) 3-month return divergence.
    EW outperforming = broad participation = healthy.
    CW outperforming = mega-cap concentration = blow-off risk.
    This directly operationalizes Druckenmiller's 1987 observation.
    """
    cw_ret = fetch_returns(SP500_CW)
    ew_ret = fetch_returns(SP500_EW)

    if cw_ret is None or ew_ret is None:
        return {"score": 50.0, "direction": "neutral",
                "ew_3m_pct": 0.0, "cw_3m_pct": 0.0, "divergence": 0.0}

    divergence = ew_ret - cw_ret  # positive = EW leading = healthy

    if divergence > 2:
        score     = min(100, 50 + divergence * 5)
        direction = "healthy"
    elif divergence < -2:
        score     = max(0, 50 + divergence * 5)
        direction = "concentrated"
    else:
        score     = 50.0
        direction = "neutral"

    return {
        "score":      round(score, 1),
        "direction":  direction,
        "ew_3m_pct":  ew_ret,
        "cw_3m_pct":  cw_ret,
        "divergence": round(divergence, 2),
    }


# ── Signal 2: Small cap vs Large cap ─────────────────────────────────────────

def score_small_vs_large() -> dict:
    """
    IWM (Russell 2000) vs SPY (S&P 500) relative performance.
    Small caps outperforming = risk-on breadth = healthy.
    Small caps lagging = defensive / concentrated = caution.
    """
    spy_ret = fetch_returns("SPY")
    iwm_ret = fetch_returns(IWM := "IWM")

    if spy_ret is None or iwm_ret is None:
        return {"score": 50.0, "direction": "neutral",
                "small_3m_pct": 0.0, "large_3m_pct": 0.0, "divergence": 0.0}

    divergence = (iwm_ret or 0) - (spy_ret or 0)

    if divergence > 2:
        score     = min(100, 50 + divergence * 4)
        direction = "healthy"
    elif divergence < -3:
        score     = max(0, 50 + divergence * 4)
        direction = "concentrated"
    else:
        score     = 50.0
        direction = "neutral"

    return {
        "score":         round(score, 1),
        "direction":     direction,
        "small_3m_pct":  iwm_ret,
        "large_3m_pct":  spy_ret,
        "divergence":    round(divergence, 2),
    }


# ── Signal 3: Sector breadth ──────────────────────────────────────────────────

def score_sector_breadth() -> dict:
    """
    Count how many of 9 sectors are in positive 3-month territory.
    8-9 positive = broad participation.
    3-4 positive = narrow / concentrated market.
    """
    positive = 0
    negative = 0
    sector_returns = {}

    for sector, etf in SECTOR_ETFS.items():
        ret = fetch_returns(etf)
        if ret is not None:
            sector_returns[sector] = ret
            if ret > 0:
                positive += 1
            else:
                negative += 1

    total = positive + negative
    if total == 0:
        return {"score": 50.0, "direction": "neutral",
                "positive_sectors": 0, "negative_sectors": 0, "sector_returns": {}}

    breadth_ratio = positive / total  # 0 to 1

    score = breadth_ratio * 100
    if breadth_ratio >= 0.75:
        direction = "healthy"
    elif breadth_ratio <= 0.44:
        direction = "concentrated"
    else:
        direction = "neutral"

    return {
        "score":             round(score, 1),
        "direction":         direction,
        "positive_sectors":  positive,
        "negative_sectors":  negative,
        "sector_returns":    sector_returns,
    }


# ── Blow-off detector ─────────────────────────────────────────────────────────

def detect_blowoff(ew_cw: dict, sm_lg: dict, sectors: dict) -> dict:
    """
    Flag blow-off if index is up strongly but breadth is NOT confirming.
    This is Druckenmiller's 1987 pattern.
    """
    reasons = []
    index_up = ew_cw.get("cw_3m_pct", 0) > 5

    if index_up and ew_cw.get("direction") == "concentrated":
        reasons.append(
            f"Cap-weight +{ew_cw['cw_3m_pct']:.1f}% but equal-weight "
            f"only +{ew_cw['ew_3m_pct']:.1f}% -- gains in mega-caps only"
        )
    if index_up and sm_lg.get("direction") == "concentrated":
        reasons.append(
            f"Russell 2000 lagging S&P 500 by {abs(sm_lg['divergence']):.1f}% -- "
            f"small caps not participating"
        )
    if index_up and sectors.get("positive_sectors", 9) <= 4:
        reasons.append(
            f"Only {sectors['positive_sectors']}/9 sectors positive -- "
            f"rally driven by handful of sectors"
        )

    return {
        "blow_off_risk": len(reasons) >= 2,
        "reasons":       reasons,
        "index_3m_pct":  ew_cw.get("cw_3m_pct", 0),
    }


# ── Composite ─────────────────────────────────────────────────────────────────

def compute_composite(ew_cw: dict, sm_lg: dict, sectors: dict) -> tuple[float, str]:
    score = (
        ew_cw["score"]   * 0.45 +
        sm_lg["score"]   * 0.25 +
        sectors["score"] * 0.30
    )
    score = round(max(0, min(100, score)), 1)

    health = (
        "healthy"      if score >= 63 else
        "deteriorating" if score <= 42 else
        "neutral"
    )
    return score, health


# ── Report ────────────────────────────────────────────────────────────────────

def build_report(composite, health, ew_cw, sm_lg, sectors, blowoff, date):
    implication = {
        "healthy": (
            "Broad participation confirmed. Equal-weight keeping pace with cap-weight. "
            "Small caps participating. Most sectors positive. "
            "Druckenmiller breadth condition met -- gains not concentrated in mega-caps."
        ),
        "neutral": (
            "Mixed breadth. Some sectors leading, others lagging. "
            "No clear blow-off pattern but not broad-based either. "
            "Use liquidity and earnings signals as primary conviction drivers."
        ),
        "deteriorating": (
            "Breadth deteriorating. Gains increasingly concentrated. "
            "Pattern matches Druckenmiller's 1987 blow-off description: "
            "'strength concentrated in high-cap stocks, broad spectrum lagging.' "
            "Reduce exposure or hedge."
        ),
    }

    blow_warning = ""
    if blowoff["blow_off_risk"]:
        blow_warning = "BLOW-OFF RISK: " + " | ".join(blowoff["reasons"])

    return {
        "skill":            "market-breadth",
        "version":          "1.1.0",
        "date":             date,
        "composite_score":  composite,
        "health":           health,
        "blow_off_risk":    blowoff["blow_off_risk"],
        "blow_off_warning": blow_warning,
        "implication":      implication[health],
        "components": {
            "ew_vs_cw":      ew_cw,
            "small_vs_large": sm_lg,
            "sector_breadth": sectors,
        },
        "source": "Yahoo Finance via yfinance (free)",
    }


def write_markdown(report: dict, path: str):
    b  = report["components"]
    sec = b["sector_breadth"]
    lines = [
        f"# Market Breadth -- {report['date']}",
        "",
        f"**Health**: `{report['health'].upper()}`",
        f"**Score**: {report['composite_score']} / 100",
    ]
    if report["blow_off_risk"]:
        lines += ["", f"**WARNING**: {report['blow_off_warning']}"]

    lines += [
        "",
        "## Implication",
        report["implication"],
        "",
        "## Component Scores",
        "| Component | Score | Signal |",
        "|-----------|-------|--------|",
        f"| EW vs CW (mega-cap concentration) | {b['ew_vs_cw']['score']} | {b['ew_vs_cw']['direction']} |",
        f"| Small vs Large cap | {b['small_vs_large']['score']} | {b['small_vs_large']['direction']} |",
        f"| Sector breadth | {b['sector_breadth']['score']} | {b['sector_breadth']['direction']} |",
        "",
        "## Detail",
        f"- Equal-weight (RSP) 3M: {b['ew_vs_cw']['ew_3m_pct']:+.1f}% | Cap-weight (SPY) 3M: {b['ew_vs_cw']['cw_3m_pct']:+.1f}% | Divergence: {b['ew_vs_cw']['divergence']:+.1f}%",
        f"- Russell 2000 3M: {b['small_vs_large']['small_3m_pct']:+.1f}% | S&P 500 3M: {b['small_vs_large']['large_3m_pct']:+.1f}%",
        f"- Sectors positive: {sec['positive_sectors']}/9",
        "",
        "## Sector Returns (3M)",
        "| Sector | Return |",
        "|--------|--------|",
    ]
    for s, r in sorted(sec.get("sector_returns", {}).items(), key=lambda x: x[1], reverse=True):
        lines.append(f"| {s} | {r:+.1f}% |")

    lines += [
        "",
        "## Druckenmiller Principle",
        "> \"My technical analysis showed that the breadth wasn't there --",
        "> the market's strength was primarily concentrated in the high",
        "> capitalization stocks, with the broad spectrum of issues lagging",
        "> well behind. This factor made the rally look like a blow-off.\"",
        "",
        f"*Source: Yahoo Finance (yfinance). Generated by market-breadth v1.1.0*",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reports/")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    date = datetime.today().strftime("%Y-%m-%d")

    print("Fetching breadth data (yfinance)...")
    print("  EW vs CW...")
    ew_cw = score_ew_vs_cw()
    print("  Small vs Large...")
    sm_lg = score_small_vs_large()
    print("  Sector breadth...")
    sectors = score_sector_breadth()

    blowoff = detect_blowoff(ew_cw, sm_lg, sectors)
    composite, health = compute_composite(ew_cw, sm_lg, sectors)
    report = build_report(composite, health, ew_cw, sm_lg, sectors, blowoff, date)

    json_path = os.path.join(args.output_dir, f"market_breadth_{date}.json")
    md_path   = os.path.join(args.output_dir, f"market_breadth_{date}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    write_markdown(report, md_path)

    print(f"\nHealth: {health.upper()} | Score: {composite}/100")
    if blowoff["blow_off_risk"]:
        print(f"BLOW-OFF RISK DETECTED")
        for r in blowoff["reasons"]:
            print(f"  - {r}")
    print(f"Sectors positive: {sectors['positive_sectors']}/9")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()