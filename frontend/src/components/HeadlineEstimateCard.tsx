import type { CostIncomeEstimate, HogangnonoComplexResult, MarketSearchResult, RegionTrendFeatures, ValuationResult } from '../types'
import { formatManwon } from '../utils/format'

interface Props {
  valuation: ValuationResult
  costIncome: CostIncomeEstimate | null
  molit: MarketSearchResult | null
  regionalTrend: RegionTrendFeatures | null
  hogangnono?: HogangnonoComplexResult | null
}

export function HeadlineEstimateCard({ valuation, costIncome, molit, regionalTrend, hogangnono }: Props) {
  const headlinePrice = costIncome ? costIncome.estimated_price : valuation.estimated_price
  const headlineLabel = costIncome ? '원가법·수익환원법 평균' : 'AI 시세추정 모델'

  const sources: string[] = [headlineLabel]
  if (molit && (molit.sale.total_matched > 0 || molit.rent.total_matched > 0)) {
    sources.push(`국토교통부 실거래가(매매 ${molit.sale.total_matched}건·전월세 ${molit.rent.total_matched}건)`)
  }
  if (hogangnono?.found) {
    sources.push('호갱노노 실거래가(실시간)')
    if (hogangnono.listings.length > 0) {
      sources.push(`호갱노노 매물(실시간) ${hogangnono.listings.length}건`)
    }
  }
  if (regionalTrend?.apt_price_trend_sale_latest != null || regionalTrend?.land_price_change_latest != null) {
    sources.push('한국부동산원 R-ONE 지역 통계')
  }

  return (
    <section className="card" style={{ textAlign: 'center', padding: '28px 20px' }}>
      <p className="hint">현재 추정시세</p>
      <p className="valuation-price" style={{ fontSize: 40, margin: '6px 0' }}>
        {formatManwon(headlinePrice)}
      </p>
      <p className="valuation-range">
        {costIncome
          ? `원가법 ${formatManwon(costIncome.cost_approach_price)} · 수익환원법 ${formatManwon(costIncome.income_approach_price)}`
          : `추정 범위 ${formatManwon(valuation.price_lower)} ~ ${formatManwon(valuation.price_upper)} (신뢰도 ${Math.round(valuation.confidence_level * 100)}%)`}
      </p>
      <div style={{ display: 'flex', gap: 6, justifyContent: 'center', flexWrap: 'wrap', marginTop: 10 }}>
        {sources.map((s) => (
          <span key={s} className="badge badge-rule">
            {s}
          </span>
        ))}
      </div>
      <p className="disclaimer" style={{ marginTop: 14 }}>
        ⚠ 위 근거 데이터를 종합한 AI 참고 추정치입니다. 최종 담보가치 판단은 심사역 검토가 필요합니다.
      </p>
    </section>
  )
}
