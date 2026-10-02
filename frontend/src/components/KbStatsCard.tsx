import { useEffect, useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ApiError, getKbPriceTrend } from '../api/client'
import type { KbPriceTrendResponse } from '../types'
import { TrendTag } from './TrendTag'

function formatPeriodLabel(period: string): string {
  const [y, m] = period.split('-')
  return `${y.slice(2)}.${m}`
}

export function KbStatsCard({ sido }: { sido: string }) {
  const [trend, setTrend] = useState<KbPriceTrendResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getKbPriceTrend(sido, 24)
      .then(setTrend)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'KB부동산 통계를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }, [sido])

  if (loading) {
    return (
      <section className="card skeleton-card" aria-busy="true">
        <div className="skeleton-block skeleton-title" />
        <div className="skeleton-block skeleton-line" />
        <div className="skeleton-block skeleton-line short" />
      </section>
    )
  }

  if (error || !trend || trend.points.length === 0) {
    return (
      <section className="card">
        <h2>지역 통계 (KB부동산)</h2>
        <p className="empty-state">{error ?? 'KB부동산 통계 데이터가 없습니다.'}</p>
      </section>
    )
  }

  const chartData = trend.points.map((p) => ({
    period: formatPeriodLabel(p.period),
    매매: p.sale_index,
    전세: p.jeonse_index,
    월세: p.wolse_index,
  }))

  const latest = trend.points[trend.points.length - 1]

  return (
    <section className="card">
      <div className="card-header">
        <h2>지역 통계 (KB부동산)</h2>
        <span className="hint">{trend.region_matched ?? trend.sido}</span>
      </div>

      <div className="stat-grid">
        <div>
          <span className="stat-label">매매가격지수</span>
          <span className="stat-value">
            {latest.sale_index != null ? latest.sale_index.toFixed(2) : '-'}
            <TrendTag value={latest.sale_change_rate} /> 
          </span>
        </div>
        <div>
          <span className="stat-label">전세가격지수</span>
          <span className="stat-value">
            {latest.jeonse_index != null ? latest.jeonse_index.toFixed(2) : '-'}
            <TrendTag value={latest.jeonse_change_rate} /> 
          </span>
        </div>
        <div>
          <span className="stat-label">월세가격지수</span>
          <span className="stat-value">
            {latest.wolse_index != null ? latest.wolse_index.toFixed(2) : '데이터 없음'}
            {latest.wolse_index != null && <TrendTag value={latest.wolse_change_rate} /> }
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="period" tick={{ fontSize: 12 }} />
          <YAxis domain={['auto', 'auto']} tick={{ fontSize: 12 }} width={44} />
          <Tooltip formatter={(value: number) => (value != null ? value.toFixed(2) : '-')} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="매매" stroke="var(--accent)" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="전세" stroke="var(--grade-safe)" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="월세" stroke="var(--grade-warning)" strokeWidth={2} dot={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>

      <p className="disclaimer" style={{ marginTop: 12 }}>
        ⚠ {trend.notice}
      </p>
    </section>
  )
}
