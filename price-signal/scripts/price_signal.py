"""
price_signal.py v1.0.0
Detects divergence between price action and fundamental expectations.

Druckenmiller (Real Vision interview, 2018):
  "If a company was reporting great earnings and the stock just didn't
   act well for 3-4 months, almost inevitably something happened that
   you didn't foresee 6 months down the road. Price was a valuable signal."

He also noted algo trading has reduced the reliability of this signal
in recent years -- so we weight this skill at only 15% in the synthesizer.

Two signals:
  1. Post-earnings price reaction (did stock go up on good earnings?)
  2. Price momentum vs sector (is stock leading or lagging its peers?)
"""

import os, json, argparse, time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf
import pandas as pd

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# Key stocks to monitor — leaders in each sector
# Focus on large-caps where price signal is most meaningful
WATCH_LIST = {
    "Technology":   ["NVDA", "MSFT", "AAPL", "META", "AMD"],
    "Financials":   ["JPM",  "GS",   "MS",   "BAC",  "BLK"],
    "Healthcare":   ["LLY",  "UNH",  "ABBV", "TMO",  "AMGN"],
    "Energy":       ["XOM",  "CVX",  "COP",  "OXY",  "SLB"],
    "Industrials":  ["CAT",  "GE",   "RTX",  "HON",  "DE"],
}

LOOKBACK_DAYS = 90  # 3 months for momentum


def fetch_price_data(ticker: str, days: int = LOOKBACK_DAYS + 10) -> pd.DataFrame:
    """Fetch OHLCV data for a ticker."""
    try:
        end   = datetime.today()
        start = end - timedelta(days=days)
        df = yf.download(ticker, start=start, end=end,
                         progress=False, auto_adjust=True)
        return df
    except Exception as e:
        print(f"    Warning: {ticker} -- {e}")
        return pd.DataFrame()


def get_earnings_reaction(ticker: str) -> dict:
    """
    Check the most recent earnings release:
    Did the stock go up or down in the 3 days after earnings?
    Positive surprise but stock falls = bearish price signal (Druck's key tell).
    """
    try:
        t    = yf.Ticker(ticker)
        hist = t.earnings_dates

        if hist is None or hist.empty:
            return {"signal": "neutral", "reaction_pct": 0.0, "has_data": False}

        # Find most recent past earnings date
        now  = pd.Timestamp.now(tz="UTC")
        past = hist[hist.index < now]
        if past.empty:
            return {"signal": "neutral", "reaction_pct": 0.0, "has_data": False}

        latest_date = past.index[0]
        surprise    = past.iloc[0].get("Surprise(%)", None)

        # Get price data around earnings
        earn_start = latest_date - timedelta(days=2)
        earn_end   = latest_date + timedelta(days=5)
        prices     = yf.download(ticker, start=earn_start, end=earn_end,
                                  progress=False, auto_adjust=True)

        if prices.empty or len(prices) < 3:
            return {"signal": "neutral", "reaction_pct": 0.0, "has_data": False}

        # 3-day post-earnings return
        def _scalar(v):
            return float(v.iloc[0]) if hasattr(v, 'iloc') else float(v)
        reaction_pct = (_scalar(prices["Close"].iloc[-1]) - _scalar(prices["Close"].iloc[0])) \
                    / _scalar(prices["Close"].iloc[0]) * 100

        # Classify signal
        # Good earnings + bad price = bearish (Druckenmiller's warning signal)
        # Bad earnings + good price = bullish (market already priced it in)
        if surprise is not None and not pd.isna(surprise):
            if surprise > 5 and reaction_pct < -2:
                signal = "bearish"   # beat estimates but stock sold off
            elif surprise < -5 and reaction_pct > 2:
                signal = "bullish"   # missed but stock held = already priced
            elif reaction_pct > 2:
                signal = "bullish"
            elif reaction_pct < -2:
                signal = "bearish"
            else:
                signal = "neutral"
        else:
            signal = "bullish" if reaction_pct > 2 else "bearish" if reaction_pct < -2 else "neutral"

        return {
            "signal":       signal,
            "reaction_pct": round(reaction_pct, 2),
            "surprise_pct": round(float(surprise), 2) if surprise and not pd.isna(surprise) else None,
            "has_data":     True,
            "earnings_date": str(latest_date.date()),
        }

    except Exception as e:
        print(f"    Warning (earnings): {ticker} -- {e}")
        return {"signal": "neutral", "reaction_pct": 0.0, "has_data": False}


def get_price_momentum(ticker: str, sector_etf: str) -> dict:
    """
    Compare stock's 3-month return vs its sector ETF.
    Stock leading sector = price signal confirming fundamentals.
    Stock lagging sector = price signal warning (Druck: "didn't act well").
    """
    try:
        stock_df  = fetch_price_data(ticker)
        sector_df = fetch_price_data(sector_etf)

        if stock_df.empty or sector_df.empty:
            return {"signal": "neutral", "stock_ret": 0.0,
                    "sector_ret": 0.0, "relative": 0.0}

        def ret(df):
            c = df["Close"].dropna()
            if len(c) < 2:
                return 0.0
            return float((c.iloc[-1].iloc[0] if hasattr(c.iloc[-1], 'iloc') else c.iloc[-1]) /
                        (c.iloc[0].iloc[0]  if hasattr(c.iloc[0],  'iloc') else c.iloc[0]) * 100 - 100)

        stock_ret  = ret(stock_df)
        sector_ret = ret(sector_df)
        relative   = stock_ret - sector_ret

        if relative > 5:
            signal = "bullish"   # stock leading sector
        elif relative < -5:
            signal = "bearish"   # stock lagging sector (Druck's warning)
        else:
            signal = "neutral"

        return {
            "signal":     signal,
            "stock_ret":  round(stock_ret, 2),
            "sector_ret": round(sector_ret, 2),
            "relative":   round(relative, 2),
        }

    except Exception as e:
        print(f"    Warning (momentum): {ticker} -- {e}")
        return {"signal": "neutral", "stock_ret": 0.0,
                "sector_ret": 0.0, "relative": 0.0}


SECTOR_ETFS = {
    "Technology":  "XLK",
    "Financials":  "XLF",
    "Healthcare":  "XLV",
    "Energy":      "XLE",
    "Industrials": "XLI",
}


def analyze_sector(sector: str, tickers: list) -> dict:
    etf = SECTOR_ETFS.get(sector, "SPY")
    ticker_results = {}

    for ticker in tickers:
        earn = get_earnings_reaction(ticker)
        mom  = get_price_momentum(ticker, etf)

        # Combine: earnings reaction 40% + momentum 60%
        signal_map = {"bullish": 1, "neutral": 0, "bearish": -1}
        combined   = (
            signal_map[earn["signal"]] * 0.4 +
            signal_map[mom["signal"]]  * 0.6
        )

        if combined > 0.2:
            final_signal = "bullish"
        elif combined < -0.2:
            final_signal = "bearish"
        else:
            final_signal = "neutral"

        ticker_results[ticker] = {
            "signal":           final_signal,
            "earnings_reaction": earn,
            "price_momentum":    mom,
        }
        time.sleep(0.2)

    # Sector aggregate
    signals    = [v["signal"] for v in ticker_results.values()]
    bullish_n  = signals.count("bullish")
    bearish_n  = signals.count("bearish")
    breadth    = (bullish_n - bearish_n) / len(tickers)

    score = 50 + breadth * 40
    score = max(0, min(100, score))

    if breadth > 0.2:
        direction = "bullish"
    elif breadth < -0.2:
        direction = "bearish"
    else:
        direction = "neutral"

    return {
        "score":     round(score, 1),
        "direction": direction,
        "bullish":   bullish_n,
        "bearish":   bearish_n,
        "tickers":   ticker_results,
    }


def compute_overall(sector_results: dict) -> tuple[float, str]:
    scores     = [v["score"] for v in sector_results.values()]
    overall    = sum(scores) / len(scores)
    bullish_s  = sum(1 for v in sector_results.values() if v["direction"] == "bullish")
    bearish_s  = sum(1 for v in sector_results.values() if v["direction"] == "bearish")

    if bullish_s >= 4:
        direction = "bullish"
    elif bearish_s >= 4:
        direction = "bearish"
    else:
        direction = "neutral"

    return round(overall, 1), direction


def build_report(overall_score, overall_direction, sector_results, date):
    implication = {
        "bullish": (
            "Price action confirming fundamentals. Stocks acting well after "
            "earnings and leading their sectors. Druckenmiller's price signal "
            "is supportive -- no hidden deterioration visible in price behavior."
        ),
        "neutral": (
            "Mixed price signals. Some stocks acting well, others lagging. "
            "No clear divergence pattern. Treat as neutral input to synthesizer. "
            "Note: Druckenmiller acknowledged algo trading has reduced reliability "
            "of this signal in recent years."
        ),
        "bearish": (
            "Price action diverging from fundamentals. Stocks not responding "
            "well to good news, or lagging sectors despite positive outlook. "
            "Druckenmiller: 'Almost inevitably something happened you didn't "
            "foresee 6 months down the road.' Consider as early warning."
        ),
    }

    # Find notable divergences (most interesting signals)
    divergences = []
    for sector, data in sector_results.items():
        for ticker, td in data["tickers"].items():
            earn = td["earnings_reaction"]
            if (earn.get("surprise_pct") or 0) > 5 and earn["signal"] == "bearish":
                divergences.append(
                    f"{ticker}: beat earnings by {earn['surprise_pct']:.1f}% "
                    f"but stock reacted {earn['reaction_pct']:+.1f}% -- warning signal"
                )

    return {
        "skill":             "price-signal",
        "version":           "1.0.0",
        "date":              date,
        "overall_score":     overall_score,
        "overall_direction": overall_direction,
        "implication":       implication[overall_direction],
        "notable_divergences": divergences,
        "sector_results":    {
            k: {kk: vv for kk, vv in v.items() if kk != "tickers"}
            for k, v in sector_results.items()
        },
        "caveat": (
            "Druckenmiller noted in 2018 that algo trading has 'severely inhibited' "
            "his ability to read price signals. This skill is weighted at 15% in "
            "the synthesizer, lower than the other three, for this reason."
        ),
        "source": "Yahoo Finance via yfinance (free)",
    }


def write_markdown(report: dict, path: str):
    lines = [
        f"# Price Signal Analysis -- {report['date']}",
        "",
        f"**Overall**: `{report['overall_direction'].upper()}`",
        f"**Score**: {report['overall_score']} / 100",
        "",
        "## Implication",
        report["implication"],
        "",
        "## Sector Signals",
        "| Sector | Score | Direction | Bullish | Bearish |",
        "|--------|-------|-----------|---------|---------|",
    ]
    for sector, data in report["sector_results"].items():
        lines.append(
            f"| {sector} | {data['score']} | {data['direction']} "
            f"| {data['bullish']} | {data['bearish']} |"
        )

    if report["notable_divergences"]:
        lines += ["", "## Notable Divergences (watch carefully)", ""]
        for d in report["notable_divergences"]:
            lines.append(f"- {d}")

    lines += [
        "",
        "## Important Caveat",
        f"> {report['caveat']}",
        "",
        "## Druckenmiller Principle",
        "> \"If a company was reporting great earnings and the stock just",
        "> didn't act well for 3-4 months, almost inevitably something",
        "> happened that you didn't foresee 6 months down the road.",
        "> Price was a valuable signal.\"",
        "",
        f"*Source: Yahoo Finance (yfinance). Generated by price-signal v1.0.0*",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reports/")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    date = datetime.today().strftime("%Y-%m-%d")

    print("Analyzing price signals (yfinance)...")
    sector_results = {}
    for sector, tickers in WATCH_LIST.items():
        print(f"  {sector}...")
        sector_results[sector] = analyze_sector(sector, tickers)

    overall_score, overall_direction = compute_overall(sector_results)
    report = build_report(overall_score, overall_direction, sector_results, date)

    json_path = os.path.join(args.output_dir, f"price_signal_{date}.json")
    md_path   = os.path.join(args.output_dir, f"price_signal_{date}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    write_markdown(report, md_path)

    print(f"\nOverall: {overall_direction.upper()} | Score: {overall_score}/100")
    if report["notable_divergences"]:
        print("Notable divergences:")
        for d in report["notable_divergences"]:
            print(f"  - {d}")
    print(f"JSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()