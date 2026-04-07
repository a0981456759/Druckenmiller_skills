# Druckenmiller Conviction Skill

一个 Claude Code skill，将 Stanley Druckenmiller 的投资框架带入你的对话——以流动性为首的四大信号分析、确信度评分、仓位建议，用他的口吻直接回答。

每天 pipeline 执行 4 个信号（流动性、前瞻盈利、市场广度、价格信号），产出确信度 JSON。Skill 读取该 JSON，像 Druckenmiller 一样回应。

---

## 快速开始 — 路线 A（使用共享数据，2 分钟）

使用现成的数据端点，不需要 API key，不需要跑 pipeline。

**1. 安装 Skill**

```bash
claude skill install https://github.com/a0981456759/druckenmiller-skill
```

或手动：将 `skills/druckenmiller/SKILL.md` 和 `skills/druckenmiller/PERSONA.md` 复制到你的 Claude Code skills 文件夹。

**2. 问 Claude**

```
今天市场怎样？
Druckenmiller 今天怎么看？
现在该持多少仓位？
```

Skill 会自动从 `https://druckenmiller-skills.vercel.app` 抓取数据。

> 数据由维护者每个工作日更新。若今日报告尚未生成，Skill 会告知你。

---

## 自架 — 路线 B（跑自己的 Pipeline）

Fork 此 repo，建立自己的数据 pipeline，完全掌控数据更新频率与 API 用量。

### 前置需求

- Python 3.10+
- [FRED API Key](https://fred.stlouisfed.org/docs/api/api_key.html)（免费）
- [FMP API Key](https://financialmodelingprep.com/developer/docs)（免费方案可用）
- Vercel 账号（免费）

### 设置步骤

**1. Fork 此 repo**

**2. 添加 API Keys 为 GitHub Secrets**

在你的 fork：`Settings → Secrets and variables → Actions`

| Secret | 内容 |
|--------|------|
| `FRED_API_KEY` | 你的 FRED key |
| `FMP_API_KEY` | 你的 FMP key |

**3. 部署到 Vercel**

将 fork 的 repo 连接到 Vercel。`public/` 文件夹为静态网站根目录，Vercel 会自动提供 `public/reports/`。

**4. 更新 Skill URL**

在 `skills/druckenmiller/SKILL.md` 中，将：
```
https://druckenmiller-skills.vercel.app
```
替换为你自己的 Vercel 部署地址。

**5. 执行 Pipeline**

从 GitHub Actions 手动触发（`Actions → Daily Conviction Pipeline → Run workflow`），或在本机执行：

```bash
pip install -r requirements.txt
cp .env.example .env  # 填入你的 API keys

python liquidity-regime/scripts/liquidity_regime.py --output-dir public/reports/
python forward-earnings/scripts/forward_earnings.py --output-dir public/reports/
python market-breadth/scripts/market_breadth.py --output-dir public/reports/
python price-signal/scripts/price_signal.py --output-dir public/reports/
python conviction-synthesizer/scripts/conviction_synthesizer.py --reports-dir public/reports/ --output-dir public/reports/
```

> **注意：** GitHub Actions 的 IP 被 Yahoo Finance 封锁，建议在本机或 VPS 上执行 pipeline，再 push reports。

---

## 运作原理

```
Pipeline（Python）
  ├── liquidity-regime/       → FRED + FMP 数据 → 流动性分数
  ├── forward-earnings/       → FMP 盈利数据 → 分析师修正趋势
  ├── market-breadth/         → 广度指标 → 市场参与健康度
  ├── price-signal/           → 盈利 vs 股价反应 → 背离检测
  └── conviction-synthesizer/ → 加权分数 → conviction_YYYY-MM-DD.json

Vercel
  └── public/reports/conviction_YYYY-MM-DD.json（静态文件托管）

Claude Code Skill
  ├── skills/druckenmiller/SKILL.md    → 抓取 JSON、解读信号
  └── skills/druckenmiller/PERSONA.md → Druckenmiller 的口吻与决策逻辑
```

### 确信度分数 → 仓位对应

| 分数 | 区间 | 股票仓位 |
|------|------|---------|
| 85–100 | Fat Pitch | 90–100%，全力出手 |
| 70–84 | High Conviction | 70–89%，积极加仓 |
| 50–69 | Moderate | 50–69%，标准仓位，等催化剂 |
| 30–49 | Low Conviction | 20–49%，减仓，现金是仓位 |
| 0–29 | Capital Preservation | 0–19%，最大防御 |

---

## 信号权重

| 信号 | 权重 | Druckenmiller 的看法 |
|------|------|----------------------|
| 流动性制度 | 35% | 「推动市场的是流动性，不是盈利。」 |
| 前瞻盈利 | 25% | 分析师修正反映的是市场共识尚未 price in 的信息 |
| 市场广度 | 25% | 涨势分散才健康；只有大型股涨是 1987 年的警示 |
| 价格信号 | 15% | 盈利好但股价跌 = 六个月后坏消息的预警 |

---

## 其他语言

- [English](README.md)
- [繁體中文](README_ZH-TW.md)

---

## 授权

MIT — 自由使用，欢迎标注来源。

*数据来源：Yahoo Finance、FRED、Financial Modeling Prep。仅供研究，非投资建议。*
