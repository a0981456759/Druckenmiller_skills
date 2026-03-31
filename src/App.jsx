import { useState, useEffect, useCallback } from 'react'
import styles from './App.module.css'

// ── helpers ───────────────────────────────────────────────────────────────────

function todayStr() {
  const d = new Date()
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function scoreColor(s) {
  if (s < 50) return styles.colorRed
  if (s <= 65) return styles.colorOrange
  return styles.colorGreen
}

function barClass(s) {
  if (s < 50) return styles.barRed
  if (s <= 65) return styles.barOrange
  return styles.barGreen
}

const ZONE_LABELS = {
  'fat pitch':            'FAT PITCH',
  'high conviction':      'HIGH CONVICTION',
  'moderate':             'MODERATE',
  'low conviction':       'LOW CONVICTION',
  'capital preservation': 'CAPITAL PRESERVATION',
}

const ZONE_STYLES = {
  'fat pitch':            styles.zoneFat,
  'high conviction':      styles.zoneHigh,
  'moderate':             styles.zoneMod,
  'low conviction':       styles.zoneLow,
  'capital preservation': styles.zonePres,
}

const SIGNAL_NAMES = {
  'liquidity-regime': '流動性制度',
  'forward-earnings': '前瞻盈利',
  'market-breadth':   '市場廣度',
  'price-signal':     '價格信號',
}

// ── CopyBlock ─────────────────────────────────────────────────────────────────

function CopyBlock({ value }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className={styles.copyBlock}>
      <code className={styles.copyCode}>{value}</code>
      <button className={`${styles.copyBtn} ${copied ? styles.copyBtnDone : ''}`} onClick={handleCopy}>
        {copied ? '已複製 ✓' : '複製'}
      </button>
    </div>
  )
}

// ── SkillModal ─────────────────────────────────────────────────────────────────

const GITHUB_REPO  = 'a0981456759/Druckenmiller_skills'
const PLUGIN_NAME  = 'druckenmiller'
const MARKET_NAME  = 'druckenmiller-skill'

function SkillModal({ onClose }) {
  const date    = todayStr()
  const jsonUrl = `${window.location.origin}/reports/conviction_${date}.json`

  const handleBackdrop = useCallback(e => {
    if (e.target === e.currentTarget) onClose()
  }, [onClose])

  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className={styles.modalOverlay} onClick={handleBackdrop}>
      <div className={styles.modal}>
        <button className={styles.modalClose} onClick={onClose}>✕</button>

        <div className={styles.modalIcon}>📊</div>
        <h2 className={styles.modalTitle}>接入 Claude Code</h2>
        <p className={styles.modalSub}>
          安裝後，直接問 Claude「今天市場怎樣」或「確信度多少」，<br />
          Claude 會自動讀取今日數據並用 Druckenmiller 框架回答。
        </p>

        {/* Method 1 — Plugin install */}
        <div className={styles.methodBlock}>
          <div className={styles.methodHeader}>
            <span className={styles.methodBadge}>推薦</span>
            <span className={styles.methodTitle}>Claude Code Plugin（兩行安裝）</span>
          </div>
          <p className={styles.methodDesc}>在終端機執行以下兩行：</p>
          <CopyBlock value={`claude plugins add ${GITHUB_REPO}`} />
          <div style={{ height: 6 }} />
          <CopyBlock value={`claude plugins install ${PLUGIN_NAME}@${MARKET_NAME}`} />
        </div>

        {/* Method 2 — Direct JSON */}
        <div className={styles.methodBlock}>
          <div className={styles.methodHeader}>
            <span className={styles.methodTitle}>直接 fetch 今日 JSON</span>
          </div>
          <p className={styles.methodDesc}>
            任何工具（curl、Python、n8n…）都可以直接 GET 今日數據。
          </p>
          <CopyBlock value={jsonUrl} />
        </div>

        <div className={styles.modalNotice}>
          數據來源：Yahoo Finance · FRED · FMP。每日自動更新。<br />
          僅供研究參考，非投資建議。
        </div>
      </div>
    </div>
  )
}

// ── SignalRow ─────────────────────────────────────────────────────────────────

function SignalRow({ name, data }) {
  const pct = Math.min(100, Math.max(0, data.score)).toFixed(0)
  return (
    <div className={styles.signalRow}>
      <div className={styles.signalTop}>
        <span className={styles.signalName}>{SIGNAL_NAMES[name] ?? name}</span>
        <span className={`${styles.signalScore} ${scoreColor(data.score)}`}>
          {data.score.toFixed(1)}
        </span>
      </div>
      <div className={styles.signalBottom}>
        <div className={styles.barTrack}>
          <div
            className={`${styles.barFill} ${barClass(data.score)}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className={styles.signalMeta}>
          {data.direction} &nbsp;·&nbsp; 權重 {Math.round(data.weight * 100)}%
          {data.stale && <span className={styles.stale}> (stale)</span>}
        </span>
      </div>
    </div>
  )
}

// ── ConvictionScale ────────────────────────────────────────────────────────────

function ConvictionScale({ score }) {
  const left = Math.min(100, Math.max(0, score)).toFixed(1)
  return (
    <div className={styles.scaleWrap}>
      <div className={styles.sectionLabel}>確信度對照尺</div>
      <div className={styles.scaleTrack}>
        <div className={styles.scaleMarker} style={{ left: `${left}%` }} />
      </div>
      <div className={styles.scaleNums}>
        {[0, 25, 50, 75, 100].map(n => <span key={n}>{n}</span>)}
      </div>
      <div className={styles.scaleZones}>
        <span className={styles.colorRed}>低確信 (0–49)</span>
        <span className={styles.colorOrange}>中確信 (50–65)</span>
        <span className={styles.colorGreen}>高確信 (66–100)</span>
      </div>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [data,      setData]      = useState(null)
  const [error,     setError]     = useState(false)
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    const date = todayStr()
    fetch(`/reports/conviction_${date}.json`)
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setData)
      .catch(() => setError(true))
  }, [])

  if (error) {
    return (
      <div className={styles.center}>
        <div className={styles.errorMsg}>
          今日數據尚未生成，請先跑 pipeline
          <div className={styles.errorSub}>run_pipeline.bat</div>
        </div>
      </div>
    )
  }

  if (!data) {
    return <div className={styles.center}><div className={styles.muted}>載入中...</div></div>
  }

  const hasDivergences = data.notable_divergences?.length > 0

  return (
    <>
      {/* Floating skill button */}
      <button className={styles.skillBtn} onClick={() => setShowModal(true)}>
        <span>📊</span> 一鍵 Skill
      </button>

      {showModal && <SkillModal onClose={() => setShowModal(false)} />}

      <div className={styles.page}>
        <div className={styles.container}>

          {/* Header */}
          <header className={styles.header}>
            <div className={styles.dateLabel}>{data.date}</div>
            <div className={styles.scoreWrap}>
              <span className={`${styles.scoreBig} ${scoreColor(data.conviction_score)}`}>
                {data.conviction_score.toFixed(1)}
              </span>
              <span className={styles.scoreMax}>/ 100</span>
            </div>
            <span className={`${styles.zoneBadge} ${ZONE_STYLES[data.conviction_zone] ?? styles.zoneMod}`}>
              {ZONE_LABELS[data.conviction_zone] ?? data.conviction_zone.toUpperCase()}
            </span>
            <div className={styles.equityRange}>建議倉位 {data.equity_range}</div>
          </header>

          {/* Action card */}
          <div className={`${styles.card} ${styles.cardGreen}`}>
            <div className={styles.cardLabel}>行動建議</div>
            <div className={styles.cardBody}>{data.action}</div>
          </div>

          {/* Divergence warning */}
          {hasDivergences && (
            <div className={`${styles.card} ${styles.cardOrange}`}>
              <div className={styles.cardLabel}>價格背離警告 (Druckenmiller Signal)</div>
              <ul className={styles.divList}>
                {data.notable_divergences.map((d, i) => (
                  <li key={i} className={styles.divItem}>
                    <span className={styles.divIcon}>▲</span>
                    <span>{d}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Signals */}
          <div className={styles.sectionLabel}>四大信號</div>
          <div className={styles.signalsList}>
            {Object.entries(data.components).map(([key, comp]) => (
              <SignalRow key={key} name={key} data={comp} />
            ))}
          </div>

          {/* Narrative */}
          <div className={styles.sectionLabel}>市場敘述</div>
          <div className={styles.narrative}>{data.narrative}</div>

          {/* Scale */}
          <ConvictionScale score={data.conviction_score} />

          {/* Quote */}
          <div className={styles.quoteWrap}>
            <div className={styles.quoteText}>"{data.druck_quote}"</div>
            <div className={styles.quoteAuthor}>— Stanley Druckenmiller</div>
          </div>

          {/* Footer */}
          <div className={styles.footer}>
            conviction-synthesizer v{data.version} &nbsp;·&nbsp; {data.date}<br />
            Based solely on principles Druckenmiller has stated publicly. Not investment advice.
          </div>

        </div>
      </div>
    </>
  )
}
