"""
conviction_synthesizer.py v1.0.0
Reads the 4 upstream skill JSONs and synthesizes into a unified
conviction score, position recommendation, and daily briefing.

Weights (based on Druckenmiller's explicit prioritization):
  liquidity-regime : 35%  -- "It's liquidity that moves markets"
  forward-earnings : 25%  -- "What people think it's going to earn"
  market-breadth   : 25%  -- "Breadth wasn't there" (1987 top call)
  price-signal     : 15%  -- "Didn't act well" (reduced due to algos)

Conviction → Position mapping:
  85-100 : Fat pitch    → 90-100% equity (swing hard)
  70-84  : High conv.  → 70-89%  equity
  50-69  : Moderate    → 50-69%  equity (standard)
  30-49  : Low conv.   → 20-49%  equity (preserve capital)
  0-29   : Protect     → 0-19%   equity (maximum defense)
"""

import os, json, argparse, glob
from datetime import datetime, timedelta

WEIGHTS = {
    "liquidity-regime": 0.35,
    "forward-earnings": 0.25,
    "market-breadth":   0.25,
    "price-signal":     0.15,
}

SCORE_KEYS = {
    "liquidity-regime": "strength",
    "forward-earnings": "overall_score",
    "market-breadth":   "composite_score",
    "price-signal":     "overall_score",
}

DIRECTION_KEYS = {
    "liquidity-regime": "regime",
    "forward-earnings": "overall_direction",
    "market-breadth":   "health",
    "price-signal":     "overall_direction",
}


def find_latest_report(reports_dir: str, skill: str) -> dict | None:
    """Find most recent JSON report for a skill."""
    pattern = os.path.join(reports_dir, f"{skill.replace('-', '_')}_*.json")
    files   = sorted(glob.glob(pattern), reverse=True)
    if not files:
        print(f"  Warning: no report found for {skill}")
        return None
    with open(files[0]) as f:
        data = json.load(f)
    age_hours = _report_age_hours(files[0])
    if age_hours > 48:
        print(f"  Warning: {skill} report is {age_hours:.0f}h old (>48h)")
        data["stale"] = True
    return data


def _report_age_hours(filepath: str) -> float:
    mtime = os.path.getmtime(filepath)
    age   = datetime.now().timestamp() - mtime
    return age / 3600


def compute_conviction(skill_data: dict) -> tuple[float, dict]:
    """Weighted average of 4 skill scores → conviction score 0-100."""
    components = {}
    weighted_sum = 0.0
    total_weight = 0.0

    for skill, weight in WEIGHTS.items():
        data = skill_data.get(skill)
        if data is None:
            continue
        score_key = SCORE_KEYS[skill]
        score     = float(data.get(score_key, 50))
        direction = data.get(DIRECTION_KEYS[skill], "neutral")
        stale     = data.get("stale", False)

        components[skill] = {
            "score":     round(score, 1),
            "direction": direction,
            "weight":    weight,
            "stale":     stale,
        }
        weighted_sum += score * weight
        total_weight += weight

    conviction = weighted_sum / total_weight if total_weight > 0 else 50.0
    return round(conviction, 1), components


def classify_conviction(score: float) -> dict:
    """Map conviction score to zone, position, and Druckenmiller quote."""
    if score >= 85:
        return {
            "zone":          "fat pitch",
            "equity_range":  "90-100%",
            "action":        "全力押注。這是 Druckenmiller 說的 fat pitch——一年只有一兩次，看到了就要全押。",
            "druck_quote":   "Soros has taught me that when you have tremendous conviction on a trade, you have to go for the jugular. It takes courage to be a pig.",
        }
    elif score >= 70:
        return {
            "zone":          "high conviction",
            "equity_range":  "70-89%",
            "action":        "積極加碼。信號清晰，可以承擔更高風險，但保留部分現金應對突發。",
            "druck_quote":   "The way to build superior long-term returns is through preservation of capital and home runs.",
        }
    elif score >= 50:
        return {
            "zone":          "moderate",
            "equity_range":  "50-69%",
            "action":        "維持標準倉位。信號偏多但不夠清晰，等待更強的催化劑再加碼。",
            "druck_quote":   "When you don't see it, don't swing.",
        }
    elif score >= 30:
        return {
            "zone":          "low conviction",
            "equity_range":  "20-49%",
            "action":        "縮減倉位，保存資本。信號混亂，現金是最好的倉位。",
            "druck_quote":   "I'm always thinking about losing money as opposed to making money.",
        }
    else:
        return {
            "zone":          "capital preservation",
            "equity_range":  "0-19%",
            "action":        "最大防禦。市場環境惡劣，等待風暴過去。",
            "druck_quote":   "The wonderful thing about our business is that it's liquid, and you can wipe the slate clean on any day.",
        }


def detect_blow_off(skill_data: dict) -> bool:
    """Check if market-breadth has flagged blow-off risk."""
    breadth = skill_data.get("market-breadth", {})
    return breadth.get("blow_off_risk", False)


def collect_divergences(skill_data: dict) -> list:
    """Collect notable price divergences from price-signal."""
    price = skill_data.get("price-signal", {})
    return price.get("notable_divergences", [])


def generate_narrative(conviction: float, components: dict,
                       blow_off: bool, divergences: list) -> str:
    """Generate a plain-language market narrative."""
    liquidity  = components.get("liquidity-regime", {})
    earnings   = components.get("forward-earnings", {})
    breadth    = components.get("market-breadth", {})
    price      = components.get("price-signal", {})

    parts = []

    # Liquidity — always lead with this (Druck's #1 factor)
    liq_dir = liquidity.get("direction", "neutral")
    liq_scr = liquidity.get("score", 50)
    if liq_dir in ["expanding", "pivot"]:
        parts.append(f"流動性環境支撐市場（{liq_scr:.0f}/100）——Fed 方向有利，這是 Druckenmiller 最重視的信號。")
    elif liq_dir == "tightening":
        parts.append(f"流動性收緊（{liq_scr:.0f}/100）——Fed 仍在抽走資金，這是最大的逆風。")
    else:
        parts.append(f"流動性中性（{liq_scr:.0f}/100）——Fed 轉向跡象存在但尚未確認，等待更明確信號。")

    # Earnings
    earn_dir = earnings.get("direction", "neutral")
    earn_scr = earnings.get("score", 50)
    if earn_dir == "beat":
        parts.append(f"分析師正在上調盈利預期（{earn_scr:.0f}/100），這是 Druckenmiller 說的「conventional wisdom 尚未反映」的機會。")
    elif earn_dir == "miss":
        parts.append(f"分析師下調盈利預期（{earn_scr:.0f}/100），市場預期正在惡化。")

    # Breadth
    breadth_health = breadth.get("direction", "neutral")
    breadth_scr    = breadth.get("score", 50)
    if breadth_health == "healthy":
        parts.append(f"市場廣度健康（{breadth_scr:.0f}/100）——漲跌勢分散，非大型股集中型市場。")
    elif breadth_health == "deteriorating":
        parts.append(f"市場廣度惡化（{breadth_scr:.0f}/100）——類似 Druckenmiller 1987 年頂部前描述的集中型漲勢。")

    # Blow-off warning
    if blow_off:
        parts.append("警告：檢測到 blow-off 風險——指數強勢但廣度不確認，Druckenmiller 視此為撤退信號。")

    # Price signal divergences
    if divergences:
        parts.append(
            f"股價信號出現 {len(divergences)} 個背離（盈利好但股價跌），"
            "Druckenmiller：「幾乎必然是六個月後的壞消息預警。」"
        )

    return " ".join(parts)


def build_report(conviction, zone_info, components, narrative,
                 blow_off, divergences, skill_data, date):
    return {
        "skill":             "conviction-synthesizer",
        "version":           "1.0.0",
        "date":              date,
        "conviction_score":  conviction,
        "conviction_zone":   zone_info["zone"],
        "equity_range":      zone_info["equity_range"],
        "action":            zone_info["action"],
        "narrative":         narrative,
        "druck_quote":       zone_info["druck_quote"],
        "blow_off_risk":     blow_off,
        "notable_divergences": divergences,
        "components":        components,
        "weights":           WEIGHTS,
    }


def write_markdown(report: dict, path: str):
    comp = report["components"]
    lines = [
        f"# Druckenmiller Conviction Briefing -- {report['date']}",
        "",
        f"## 今日判斷",
        f"**確信度**: {report['conviction_score']} / 100  ",
        f"**區間**: {report['conviction_zone'].upper()}  ",
        f"**建議倉位**: {report['equity_range']}",
        "",
        f"## 行動建議",
        report["action"],
        "",
        f"## 市場敘述",
        report["narrative"],
    ]

    if report["blow_off_risk"]:
        lines += ["", "## 警告", "**Blow-off 風險已觸發** — 建議降低倉位上限至 50%"]

    if report["notable_divergences"]:
        lines += ["", "## 價格背離警告 (Druckenmiller Signal)"]
        for d in report["notable_divergences"]:
            lines.append(f"- {d}")

    lines += [
        "",
        "## 四大信號明細",
        "| 信號 | 分數 | 方向 | 權重 |",
        "|------|------|------|------|",
    ]
    for skill, data in comp.items():
        stale_flag = " (stale)" if data.get("stale") else ""
        lines.append(
            f"| {skill} | {data['score']} | {data['direction']} "
            f"| {int(data['weight']*100)}%{stale_flag} |"
        )

    lines += [
        "",
        "## Druckenmiller 語錄",
        f"> \"{report['druck_quote']}\"",
        "",
        "---",
        f"*Generated by conviction-synthesizer v1.0.0 on {report['date']}*",
        "*Based solely on principles Druckenmiller has stated publicly.*",
        "*Not investment advice.*",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/")
    parser.add_argument("--output-dir",  default="reports/")
    args = parser.parse_args()

    date = datetime.today().strftime("%Y-%m-%d")
    os.makedirs(args.output_dir, exist_ok=True)

    print("Loading upstream skill reports...")
    skill_data = {}
    for skill in WEIGHTS:
        data = find_latest_report(args.reports_dir, skill)
        skill_data[skill] = data

    print("Computing conviction score...")
    conviction, components = compute_conviction(skill_data)
    zone_info  = classify_conviction(conviction)
    blow_off   = detect_blow_off(skill_data)
    divergences = collect_divergences(skill_data)
    narrative  = generate_narrative(conviction, components, blow_off, divergences)

    report = build_report(
        conviction, zone_info, components, narrative,
        blow_off, divergences, skill_data, date
    )

    json_path = os.path.join(args.output_dir, f"conviction_{date}.json")
    md_path   = os.path.join(args.output_dir, f"conviction_{date}.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    write_markdown(report, md_path)

    print(f"\n{'='*50}")
    print(f"確信度: {conviction}/100  ({zone_info['zone'].upper()})")
    print(f"建議倉位: {zone_info['equity_range']}")
    print(f"{'='*50}")
    print(f"\n{zone_info['action']}")
    if blow_off:
        print("\nWARNING: Blow-off risk detected!")
    if divergences:
        print(f"\n{len(divergences)} price divergence(s) detected:")
        for d in divergences:
            print(f"  - {d}")
    print(f"\nJSON: {json_path}")
    print(f"MD:   {md_path}")


if __name__ == "__main__":
    main()