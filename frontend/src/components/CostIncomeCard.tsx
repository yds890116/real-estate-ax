import type { CostIncomeEstimate } from '../types'
import { formatManwon } from '../utils/format'

export function CostIncomeCard({ estimate }: { estimate: CostIncomeEstimate }) {
  return (
    <section className="card">
      <div className="card-header">
        <h2>원가법·수익환원법 추정 근거</h2>
        <span className="badge badge-rule">{estimate.property_type}</span>
      </div>

      <div className="results-grid">
        <div>
          <p className="opinion-label">원가법(Cost Approach)</p>
          <div className="stat-grid">
            <div>
              <span className="stat-label">재조달원가 단가</span>
              <span className="stat-value">{estimate.replacement_cost_per_area.toLocaleString('ko-KR')}만원/㎡</span>
            </div>
            <div>
              <span className="stat-label">감가율</span>
              <span className="stat-value">{estimate.depreciation_rate_pct}%</span>
            </div>
            <div>
              <span className="stat-label">적산가격</span>
              <span className="stat-value">{formatManwon(estimate.cost_approach_price)}</span>
            </div>
          </div>
        </div>

        <div>
          <p className="opinion-label">수익환원법(Income Capitalization)</p>
          <div className="stat-grid">
            <div>
              <span className="stat-label">임대료 단가</span>
              <span className="stat-value">{estimate.unit_rent_per_area}만원/㎡/월</span>
            </div>
            <div>
              <span className="stat-label">환원율(공실률/경비율)</span>
              <span className="stat-value">
                {estimate.cap_rate_pct}% ({estimate.vacancy_rate_pct}%/{estimate.opex_ratio_pct}%)
              </span>
            </div>
            <div>
              <span className="stat-label">수익가격</span>
              <span className="stat-value">{formatManwon(estimate.income_approach_price)}</span>
            </div>
          </div>
        </div>
      </div>

      <p className="valuation-price" style={{ fontSize: 20, marginTop: 8 }}>
        두 접근법 평균 {formatManwon(estimate.estimated_price)}
      </p>
      <p className="valuation-range">㎡당 {estimate.price_per_area.toLocaleString('ko-KR')}만원 · 신뢰도 {Math.round(estimate.confidence_level * 100)}%</p>

      <p className="disclaimer">⚠ {estimate.disclaimer}</p>
    </section>
  )
}
