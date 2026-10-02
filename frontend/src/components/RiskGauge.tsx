interface Props {
  /** 0~100, 높을수록 고위험 */
  score: number
  grade: number
  gradeLabel: string
  size?: number
}

const CX = 100
const CY = 96
const RADIUS = 78
const STROKE = 16

function polarPoint(angleDeg: number, radius: number) {
  const rad = (angleDeg * Math.PI) / 180
  return { x: CX + radius * Math.cos(rad), y: CY - radius * Math.sin(rad) }
}

function arcPath(startAngle: number, endAngle: number, radius: number) {
  const start = polarPoint(startAngle, radius)
  const end = polarPoint(endAngle, radius)
  const largeArc = startAngle - endAngle > 180 ? 1 : 0
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`
}

/** 담보 리스크 등급(0~100 점수, 높을수록 고위험)을 반원형 게이지로 시각화한다. */
export function RiskGauge({ score, grade, gradeLabel, size = 200 }: Props) {
  const clamped = Math.max(0, Math.min(100, score))
  const needleAngle = 180 - clamped * 1.8
  const needleTip = polarPoint(needleAngle, RADIUS - STROKE / 2 - 2)

  return (
    <div className="risk-gauge" style={{ width: size }}>
      <svg viewBox="0 0 200 116" width="100%" style={{ overflow: 'visible' }}>
        <path d={arcPath(180, 120, RADIUS)} stroke="var(--grade-safe)" strokeWidth={STROKE} strokeLinecap="round" fill="none" />
        <path d={arcPath(120, 60, RADIUS)} stroke="var(--grade-caution)" strokeWidth={STROKE} strokeLinecap="round" fill="none" />
        <path d={arcPath(60, 0, RADIUS)} stroke="var(--grade-danger)" strokeWidth={STROKE} strokeLinecap="round" fill="none" />
        <line x1={CX} y1={CY} x2={needleTip.x} y2={needleTip.y} stroke="var(--text-primary)" strokeWidth={3} strokeLinecap="round" />
        <circle cx={CX} cy={CY} r={7} fill="var(--text-primary)" />
      </svg>
      <div className="risk-gauge-readout">
        <span className={`risk-gauge-grade grade-text-${gradeTone(grade)}`}>{grade}</span>
        <span className="risk-gauge-label">{gradeLabel}</span>
      </div>
    </div>
  )
}

function gradeTone(grade: number): 'safe' | 'caution' | 'danger' {
  if (grade <= 4) return 'safe'
  if (grade <= 7) return 'caution'
  return 'danger'
}
