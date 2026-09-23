import type { RegionTrendFeatures } from '../types'

function ChangeBadge({ value }: { value: number | null }) {
  if (value == null) return <span className="hint">-</span>
  const cls = value > 0 ? 'impact-negative' : value < 0 ? 'impact-positive' : ''
  return (
    <span className={`factor-item ${cls}`} style={{ display: 'inline-block', padding: '2px 8px' }}>
      {value > 0 ? '+' : ''}
      {value.toFixed(2)}%
    </span>
  )
}

export function RegionalTrendCard({ trend }: { trend: RegionTrendFeatures }) {
  const rows = [
    {
      label: '아파트 매매가격지수',
      latest: trend.apt_price_trend_sale_latest,
      change: trend.apt_price_trend_sale_mom_change_pct,
      unit: '',
    },
    {
      label: '아파트 전세가격지수',
      latest: trend.apt_price_trend_jeonse_latest,
      change: trend.apt_price_trend_jeonse_mom_change_pct,
      unit: '',
    },
    {
      label: '공동주택 실거래가격지수',
      latest: trend.apt_actual_txn_sale_latest,
      change: trend.apt_actual_txn_sale_mom_change_pct,
      unit: '',
    },
  ]

  return (
    <section className="card">
      <div className="card-header">
        <h2>지역 통계 (R-ONE)</h2>
        <span className="hint">{trend.region_matched ?? `${trend.sido} ${trend.sigungu ?? ''}`}</span>
      </div>

      <div className="risk-category-list">
        {rows.map((r) => (
          <div key={r.label} className="risk-category-detail" style={{ cursor: 'default' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="factor-name">{r.label}</span>
              <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className="stat-value">{r.latest != null ? r.latest.toFixed(2) : '데이터 없음'}</span>
                <ChangeBadge value={r.change} />
              </span>
            </div>
          </div>
        ))}

        <div className="risk-category-detail" style={{ cursor: 'default' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="factor-name">지가변동률</span>
            <span className="stat-value">
              {trend.land_price_change_latest != null ? `${trend.land_price_change_latest.toFixed(3)}%` : '데이터 없음'}
              {trend.land_price_change_period && <span className="hint"> ({trend.land_price_change_period})</span>}
            </span>
          </div>
        </div>

        <div className="risk-category-detail" style={{ cursor: 'default' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="factor-name">임대동향지수(오피스)</span>
            <span className="stat-value">
              {trend.rental_trend_office_latest != null ? trend.rental_trend_office_latest.toFixed(2) : '데이터 없음'}
              {trend.rental_trend_office_period && <span className="hint"> ({trend.rental_trend_office_period})</span>}
            </span>
          </div>
        </div>
      </div>

      <p className="disclaimer">⚠ 한국부동산원 R-ONE 통계 기준이며, 해당 지역에 세부 통계가 없으면 상위 지역(시도) 값으로 대체 표시됩니다.</p>
    </section>
  )
}
