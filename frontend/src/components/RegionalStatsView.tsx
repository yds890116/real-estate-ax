import { useEffect, useState } from 'react'
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ApiError, getRegionalStatsTrend, listRegionalStatsRegions } from '../api/client'
import type { RegionalBidStatTrend } from '../types'

function formatPeriod(period: string): string {
  if (period.length === 6) return `${period.slice(0, 4)}.${period.slice(4, 6)}`
  return period
}

export function RegionalStatsView() {
  const [regions, setRegions] = useState<string[]>([])
  const [selectedSido, setSelectedSido] = useState<string>('')
  const [trend, setTrend] = useState<RegionalBidStatTrend | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listRegionalStatsRegions()
      .then((list) => {
        setRegions(list)
        if (list.length > 0) setSelectedSido((prev) => prev || list[0])
      })
      .catch(() => setRegions([]))
  }, [])

  useEffect(() => {
    if (!selectedSido) return
    setLoading(true)
    setError(null)
    getRegionalStatsTrend(selectedSido)
      .then(setTrend)
      .catch((e) => setError(e instanceof ApiError ? e.message : '지역별 입찰 통계를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }, [selectedSido])

  const data = (trend?.items ?? []).map((item) => ({
    period: formatPeriod(item.period),
    bidCount: item.bid_count ?? 0,
    winRate: item.win_rate ?? 0,
    avgBidRate: item.avg_bid_rate_vs_appraisal ?? 0,
  }))

  return (
    <div className="search-view">
      <section className="card">
        <div className="card-header">
          <h2>지역별 입찰 통계</h2>
          <span className="hint">온비드 공매 낙찰 데이터 기반 참고 지표</span>
        </div>

        <div className="search-form-row">
          <select value={selectedSido} onChange={(e) => setSelectedSido(e.target.value)}>
            {regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        {trend && (
          <p className="disclaimer" style={{ marginTop: 12 }}>
            ⚠ {trend.notice}
          </p>
        )}
      </section>

      {loading && <div className="placeholder">통계를 불러오는 중입니다...</div>}
      {error && <div className="error-banner">⚠ {error}</div>}

      {!loading && !error && trend && data.length > 0 && (
        <section className="card">
          <div className="card-header">
            <h2>{trend.sido} 입찰 건수 · 낙찰률 · 평균 낙찰가율 추이</h2>
            <span className={`badge ${trend.is_sample_data ? 'badge-rule' : 'badge-ml'}`}>
              {trend.is_sample_data ? '샘플 데이터' : '실시간 수집'}
            </span>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="period" tick={{ fontSize: 12 }} />
              <YAxis
                yAxisId="count"
                tick={{ fontSize: 12 }}
                width={48}
                label={{ value: '건수', angle: -90, position: 'insideLeft', fontSize: 11 }}
              />
              <YAxis
                yAxisId="rate"
                orientation="right"
                tick={{ fontSize: 12 }}
                width={48}
                label={{ value: '%', angle: 90, position: 'insideRight', fontSize: 11 }}
              />
              <Tooltip
                formatter={(value, key) => {
                  if (key === 'bidCount') return [`${Number(value).toLocaleString('ko-KR')}건`, '입찰 건수']
                  if (key === 'winRate') return [`${Number(value).toFixed(1)}%`, '낙찰률']
                  return [`${Number(value).toFixed(1)}%`, '평균 낙찰가율']
                }}
              />
              <Bar yAxisId="count" dataKey="bidCount" fill="var(--accent-soft)" stroke="var(--accent)" radius={[4, 4, 0, 0]} />
              <Line yAxisId="rate" type="monotone" dataKey="winRate" stroke="var(--grade-good)" strokeWidth={2} dot={{ r: 3 }} />
              <Line yAxisId="rate" type="monotone" dataKey="avgBidRate" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
          <div className="risk-category-list">
            <span className="hint">■ 막대: 입찰 건수 (좌측 축) · — 초록선: 낙찰률(%) · — 파란선: 평균 낙찰가율(%, 감정가 대비, 우측 축)</span>
          </div>
        </section>
      )}

      {!loading && !error && trend && data.length === 0 && (
        <div className="placeholder">해당 지역의 입찰 통계 데이터가 없습니다.</div>
      )}
    </div>
  )
}
