interface Props {
  value: number | null
  /** "up-bad"(기본값): 값이 오르면 위험 신호(빨강), 내리면 안전 신호(초록) - 가격변동률 등
   *  "up-good": 값이 오르면 긍정 신호(초록) - 전세가율 등 높을수록 안전한 지표용 */
  polarity?: 'up-bad' | 'up-good'
  suffix?: string
  decimals?: number
}

export function TrendTag({ value, polarity = 'up-bad', suffix = '%', decimals = 2 }: Props) {
  if (value == null) return <span className="trend-tag trend-tag-flat">-</span>

  const isUp = value > 0
  const isFlat = value === 0
  const isGood = isFlat ? true : polarity === 'up-bad' ? !isUp : isUp
  const tone = isFlat ? 'flat' : isGood ? 'positive' : 'negative'

  return (
    <span className={`trend-tag trend-tag-${tone}`}>
      {!isFlat && <span className="trend-tag-arrow">{isUp ? '▲' : '▼'}</span>}
      {Math.abs(value).toFixed(decimals)}
      {suffix}
    </span>
  )
}
