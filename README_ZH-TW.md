# Druckenmiller Conviction Skill

一個 Claude Code skill，將 Stanley Druckenmiller 的投資框架帶入你的對話——以流動性為首的四大信號分析、確信度評分、倉位建議，用他的口吻直接回答。

每天 pipeline 執行 4 個信號（流動性、前瞻盈利、市場廣度、價格信號），產出確信度 JSON。Skill 讀取該 JSON，像 Druckenmiller 一樣回應。

---

## 快速開始 — 路線 A（使用共享數據，2 分鐘）

使用現成的數據端點，不需要 API key，不需要跑 pipeline。

**1. 安裝 Skill**

```bash
claude skill install https://github.com/a0981456759/druckenmiller-skill
```

或手動：將 `skills/druckenmiller/SKILL.md` 和 `skills/druckenmiller/PERSONA.md` 複製到你的 Claude Code skills 資料夾。

**2. 問 Claude**

```
今天市場怎樣？
Druckenmiller 今天怎麼看？
現在該持多少倉位？
```

Skill 會自動從 `https://druckenmiller-skills.vercel.app` 抓取數據。

> 數據由維護者每個工作日更新。若今日報告尚未生成，Skill 會告知你。

---

## 自架 — 路線 B（跑自己的 Pipeline）

Fork 此 repo，建立自己的數據 pipeline，完全掌控數據更新頻率與 API 用量。

### 前置需求

- Python 3.10+
- [FRED API Key](https://fred.stlouisfed.org/docs/api/api_key.html)（免費）
- [FMP API Key](https://financialmodelingprep.com/developer/docs)（免費方案可用）
- Vercel 帳號（免費）

### 設定步驟

**1. Fork 此 repo**

**2. 新增 API Keys 為 GitHub Secrets**

在你的 fork：`Settings → Secrets and variables → Actions`

| Secret | 內容 |
|--------|------|
| `FRED_API_KEY` | 你的 FRED key |
| `FMP_API_KEY` | 你的 FMP key |

**3. 部署到 Vercel**

將 fork 的 repo 連接到 Vercel。`public/` 資料夾為靜態網站根目錄，Vercel 會自動提供 `public/reports/`。

**4. 更新 Skill URL**

在 `skills/druckenmiller/SKILL.md` 中，將：
```
https://druckenmiller-skills.vercel.app
```
替換為你自己的 Vercel 部署網址。

**5. 執行 Pipeline**

從 GitHub Actions 手動觸發（`Actions → Daily Conviction Pipeline → Run workflow`），或在本機執行：

```bash
pip install -r requirements.txt
cp .env.example .env  # 填入你的 API keys

python liquidity-regime/scripts/liquidity_regime.py --output-dir public/reports/
python forward-earnings/scripts/forward_earnings.py --output-dir public/reports/
python market-breadth/scripts/market_breadth.py --output-dir public/reports/
python price-signal/scripts/price_signal.py --output-dir public/reports/
python conviction-synthesizer/scripts/conviction_synthesizer.py --reports-dir public/reports/ --output-dir public/reports/
```

> **注意：** GitHub Actions 的 IP 被 Yahoo Finance 封鎖，建議在本機或 VPS 上執行 pipeline，再 push reports。

---

## 運作原理

```
Pipeline（Python）
  ├── liquidity-regime/       → FRED + FMP 數據 → 流動性分數
  ├── forward-earnings/       → FMP 盈利數據 → 分析師修正趨勢
  ├── market-breadth/         → 廣度指標 → 市場參與健康度
  ├── price-signal/           → 盈利 vs 股價反應 → 背離偵測
  └── conviction-synthesizer/ → 加權分數 → conviction_YYYY-MM-DD.json

Vercel
  └── public/reports/conviction_YYYY-MM-DD.json（靜態檔案托管）

Claude Code Skill
  ├── skills/druckenmiller/SKILL.md    → 抓取 JSON、解讀信號
  └── skills/druckenmiller/PERSONA.md → Druckenmiller 的口吻與決策邏輯
```

### 確信度分數 → 倉位對應

| 分數 | 區間 | 股票倉位 |
|------|------|---------|
| 85–100 | Fat Pitch | 90–100%，全力出手 |
| 70–84 | High Conviction | 70–89%，積極加碼 |
| 50–69 | Moderate | 50–69%，標準倉位，等催化劑 |
| 30–49 | Low Conviction | 20–49%，縮倉，現金是倉位 |
| 0–29 | Capital Preservation | 0–19%，最大防禦 |

---

## 信號權重

| 信號 | 權重 | Druckenmiller 的看法 |
|------|------|----------------------|
| 流動性制度 | 35% | 「推動市場的是流動性，不是盈利。」 |
| 前瞻盈利 | 25% | 分析師修正反映的是市場共識尚未 price in 的資訊 |
| 市場廣度 | 25% | 漲勢分散才健康；只有大型股漲是 1987 年的警訊 |
| 價格信號 | 15% | 盈利好但股價跌 = 六個月後壞消息的預警 |

---

## 其他語言

- [English](README.md)
- [简体中文](README_ZH-CN.md)

---

## 授權

MIT — 自由使用，歡迎標注來源。

*數據來源：Yahoo Finance、FRED、Financial Modeling Prep。僅供研究，非投資建議。*
