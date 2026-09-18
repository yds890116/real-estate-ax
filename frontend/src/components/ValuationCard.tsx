import type { ValuationResult } from '../types'
import { formatManwon, formatPercent } from '../utils/format'

export function ValuationCard({ valuation }: { valuation: ValuationResult }) {
  const isMlModel = valuation.model_version.startsWith('xgboost')

  return (
    <section className="card">
      <div className="card-header">
        <h2>AI 추정 시세</h2>
        <span className={`badge ${isMlModel ? 'badge-ml' : 'badge-rule'}`}>
          {isMlModel ? 'XGBoost 모델' : '규칙 기반'}
        </span>
      </div>

      <p className="valuation-price">{formatManwon(valuation.estimated_price)}</p>
      <p className="valuation-range">
        추정 범위 {formatManwon(valuation.price_lower)} ~ {formatManwon(valuation.price_upper)}
      </p>

      <div className="stat-grid">
        <div>
          <span className="stat-label">평당 단가</span>
          <span className="stat-value">{formatManwon(valuation.price_per_area)}/㎡</span>
        </div>
        <div>
          <span className="stat-label">신뢰도</span>
          <span className="stat-value">{formatPercent(valuation.confidence_level)}</span>
        </div>
        <div>
          <span className="stat-label">비교사례</span>
          <span className="stat-value">{valuation.comparable_count.toLocaleString('ko-KR')}건</span>
        </div>
      </div>

      <p className="model-version">모델: {valuation.model_version}</p>
      <p className="disclaimer">⚠ {valuation.disclaimer}</p>
    </section>
  )
}
