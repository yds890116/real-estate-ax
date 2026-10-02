import type { RiskScoreResult } from '../types'
import { tierColorClass } from '../utils/risk'
import { RiskCategoryChart } from './RiskCategoryChart'
import { RiskGauge } from './RiskGauge'

export function RiskCard({ risk }: { risk: RiskScoreResult }) {
  return (
    <section className="card">
      <div className="card-header">
        <h2>담보 리스크 등급</h2>
        <span className={`tier-badge ${tierColorClass(risk.grade_tier)}`}>종합판정 {risk.grade_tier}</span>
      </div>

      <div className="risk-grade-row">
        <RiskGauge score={risk.score} grade={risk.risk_grade} gradeLabel={risk.risk_level_label} size={140} />
        <p className="risk-score">종합점수 {risk.score} / 100</p>
      </div>

      <p className="opinion-label">카테고리별 기여도</p>
      <RiskCategoryChart categories={risk.categories} />

      <div className="risk-category-list">
        {risk.categories.map((cat) => (
          <details key={cat.key} className="risk-category-detail">
            <summary>
              <span className="factor-name">{cat.label}</span>
              <span className="factor-weight">
                {cat.normalized_score.toFixed(0)}점 · 가중치 {Math.round(cat.weight * 100)}% · 기여 {cat.contribution.toFixed(1)}점
              </span>
            </summary>
            <ul className="factor-list">
              {cat.indicators.map((ind) => (
                <li key={ind.key} className={`factor-item impact-${ind.normalized_score >= 50 ? 'negative' : 'positive'}`}>
                  <div className="factor-item-header">
                    <span className="factor-name">{ind.label}</span>
                    <span className={`method-tag method-${ind.method}`}>{ind.method === 'ml' ? 'ML' : '규칙'}</span>
                    <span className="factor-weight">{ind.normalized_score.toFixed(0)}점</span>
                  </div>
                  <p className="factor-description">
                    {ind.description}
                    {!ind.available && ' (데이터 부족으로 중립값 적용)'}
                  </p>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>

      <p className="model-version">모델: {risk.model_version}</p>
      <p className="disclaimer">⚠ {risk.disclaimer}</p>
    </section>
  )
}
