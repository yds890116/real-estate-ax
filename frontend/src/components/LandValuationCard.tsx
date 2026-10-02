import type { LandValuationResult } from '../types'
import { TrendTag } from './TrendTag'

function scoreColorClass(score: number | null): string {
  if (score == null) return ''
  if (score >= 70) return 'grade-safe'
  if (score >= 50) return 'grade-good'
  if (score >= 30) return 'grade-caution'
  return 'grade-warning'
}

export function LandValuationCard({ valuation }: { valuation: LandValuationResult }) {
  const { characteristics: c, development_potential: dp, location_value: lv } = valuation

  return (
    <section className="card">
      <div className="card-header">
        <h2>토지 특성 및 개발잠재력</h2>
        {valuation.land_valuation_score != null && (
          <span className={`risk-grade-badge-sm ${scoreColorClass(valuation.land_valuation_score)}`}>
            {Math.round(valuation.land_valuation_score)}
          </span>
        )}
      </div>

      <div className="stat-grid">
        <div>
          <span className="stat-label">지목</span>
          <span className="stat-value">{c.jimok ?? '확인 불가'}</span>
        </div>
        <div>
          <span className="stat-label">용도지역{c.land_use_district ? ' / 용도지구' : ''}</span>
          <span className="stat-value">
            {c.land_use_zone ?? '확인 불가'}
            {c.land_use_district ? ` / ${c.land_use_district}` : ''}
          </span>
        </div>
        <div>
          <span className="stat-label">개별공시지가</span>
          <span className="stat-value">
            {c.official_land_price != null ? `${c.official_land_price.toLocaleString('ko-KR')}원/㎡` : '확인 불가'}
          </span>
        </div>
      </div>
      {!c.available && (
        <p className="hint" style={{ marginBottom: 12 }}>
          {c.notice}
        </p>
      )}

      <div className="risk-category-list">
        <div className="risk-category-detail" style={{ cursor: 'default' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="factor-name">개발잠재력 지수</span>
            <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span className="stat-value">
                {dp.development_potential_index != null ? `${dp.development_potential_index.toFixed(0)}점` : '산출 불가'}
              </span>
              {dp.legal_far_cap_pct != null && (
                <span className="hint">
                  (법정 용적률 {dp.legal_far_cap_pct}% / 건폐율 {dp.legal_bcr_cap_pct}%
                  {dp.current_floors != null ? ` · 현재 ${dp.current_floors}층/추정상한 ${dp.implied_max_floors}층` : ''})
                </span>
              )}
            </span>
          </div>
        </div>

        <div className="risk-category-detail" style={{ cursor: 'default' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="factor-name">입지가치</span>
            <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span className="stat-value">
                {lv.location_value_score != null ? `${lv.location_value_score.toFixed(0)}점` : '산출 불가'}
              </span>
              <span className="hint">
                {lv.nearest_subway_name
                  ? `${lv.nearest_subway_name} ${Math.round(lv.nearest_subway_distance_m ?? 0).toLocaleString('ko-KR')}m`
                  : '최근접역 확인 불가'}
                {lv.road_type ? ` · 접면도로: ${lv.road_type}` : ''}
              </span>
            </span>
          </div>
        </div>

        <div className="risk-category-detail" style={{ cursor: 'default' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="factor-name">지가변동률 / 토지 실거래가</span>
            <span className="stat-value">
              <TrendTag value={valuation.land_price_change_pct} decimals={3} />
              {' · '}
              {valuation.land_trade_price_per_sqm != null
                ? `${Math.round(valuation.land_trade_price_per_sqm).toLocaleString('ko-KR')}원/㎡`
                : '토지 실거래가 확인 불가'}
            </span>
          </div>
        </div>
      </div>

      <p className="disclaimer">{valuation.disclaimer}</p>
    </section>
  )
}
