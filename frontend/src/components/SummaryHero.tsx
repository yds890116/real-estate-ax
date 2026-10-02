import { useMemo } from 'react'
import type {
  CostIncomeEstimate,
  HogangnonoComplexResult,
  MarketSearchResult,
  MarketTransaction,
  RegionTrendFeatures,
  RiskScoreResult,
  ValuationResult,
} from '../types'
import { formatManwon } from '../utils/format'
import { RiskGauge } from './RiskGauge'
import { Sparkline } from './Sparkline'

interface Props {
  valuation: ValuationResult
  costIncome: CostIncomeEstimate | null
  molit: MarketSearchResult | null
  regionalTrend: RegionTrendFeatures | null
  hogangnono?: HogangnonoComplexResult | null
  risk: RiskScoreResult
  transactions: MarketTransaction[]
}

function buildSparklineData(transactions: MarketTransaction[]) {
  const buckets = new Map<string, { sum: number; count: number }>()
  for (const t of transactions) {
    const month = t.deal_date.slice(0, 7)
    const bucket = buckets.get(month) ?? { sum: 0, count: 0 }
    bucket.sum += t.deal_price / t.exclusive_area
    bucket.count += 1
    buckets.set(month, bucket)
  }
  return Array.from(buckets.entries())
    .map(([month, { sum, count }]) => ({ label: month, value: Math.round(sum / count) }))
    .sort((a, b) => a.label.localeCompare(b.label))
}

export function SummaryHero({ valuation, costIncome, molit, regionalTrend, hogangnono, risk, transactions }: Props) {
  const headlinePrice = costIncome ? costIncome.estimated_price : valuation.estimated_price
  const headlineLabel = costIncome ? '원가법·수익환원법 평균' : 'AI 시세추정 모델'
  const sparklineData = useMemo(() => buildSparklineData(transactions), [transactions])

  const sources: string[] = [headlineLabel]
  if (molit && (molit.sale.total_matched > 0 || molit.rent.total_matched > 0)) {
    sources.push(`국토부 실거래가 ${molit.sale.total_matched + molit.rent.total_matched}건`)
  }
  if (hogangnono?.found) {
    sources.push('호갱노노 실시간')
  }
  if (regionalTrend?.apt_price_trend_sale_latest != null || regionalTrend?.land_price_change_latest != null) {
    sources.push('R-ONE 지역 통계')
  }

  return (
    <section className="summary-hero">
      <div className="summary-hero-main">
        <p className="summary-hero-eyebrow">🤖 AI 참고 추정 — 심사역 검토 전 초안</p>
        <p className="summary-hero-price">{formatManwon(headlinePrice)}</p>
        <p className="summary-hero-range">
          {costIncome
            ? `원가법 ${formatManwon(costIncome.cost_approach_price)} · 수익환원법 ${formatManwon(costIncome.income_approach_price)}`
            : `추정 범위 ${formatManwon(valuation.price_lower)} ~ ${formatManwon(valuation.price_upper)} · 신뢰도 ${Math.round(valuation.confidence_level * 100)}%`}
        </p>
        <div className="summary-hero-sources">
          {sources.map((s) => (
            <span key={s} className="badge badge-rule">
              {s}
            </span>
          ))}
        </div>

        {sparklineData.length >= 2 && (
          <div>
            <div className="summary-hero-sparkline-label">
              <span>실거래 단가 추이</span>
              <span>만원/㎡</span>
            </div>
            <Sparkline data={sparklineData} formatValue={(v) => `${v.toLocaleString('ko-KR')}만원/㎡`} />
          </div>
        )}
      </div>

      <div className="summary-hero-gauge">
        <span className="summary-hero-gauge-title">담보 리스크 등급</span>
        <RiskGauge score={risk.score} grade={risk.risk_grade} gradeLabel={risk.risk_level_label} size={180} />
        <span className="summary-hero-gauge-score">종합점수 {risk.score} / 100</span>
      </div>
    </section>
  )
}
