import { useMemo } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { MarketTransaction } from '../types'

interface MonthlyPoint {
  month: string
  avgPricePerArea: number
  count: number
}

function buildMonthlySeries(transactions: MarketTransaction[]): MonthlyPoint[] {
  const buckets = new Map<string, { sum: number; count: number }>()

  for (const t of transactions) {
    const month = t.deal_date.slice(0, 7) // YYYY-MM
    const pricePerArea = t.deal_price / t.exclusive_area
    const bucket = buckets.get(month) ?? { sum: 0, count: 0 }
    bucket.sum += pricePerArea
    bucket.count += 1
    buckets.set(month, bucket)
  }

  return Array.from(buckets.entries())
    .map(([month, { sum, count }]) => ({
      month,
      avgPricePerArea: Math.round(sum / count),
      count,
    }))
    .sort((a, b) => a.month.localeCompare(b.month))
}

export function PriceTrendChart({ transactions }: { transactions: MarketTransaction[] }) {
  const data = useMemo(() => buildMonthlySeries(transactions), [transactions])

  if (data.length === 0) {
    return (
      <section className="card">
        <h2>실거래가 추이</h2>
        <p className="empty-state">해당 지역의 수집된 실거래가 데이터가 없습니다.</p>
      </section>
    )
  }

  return (
    <section className="card">
      <div className="card-header">
        <h2>월별 실거래 단가 추이</h2>
        <span className="hint">최근 {transactions.length.toLocaleString('ko-KR')}건 기준, 만원/㎡</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="month" tick={{ fontSize: 12 }} />
          <YAxis
            tick={{ fontSize: 12 }}
            width={64}
            tickFormatter={(v: number) => v.toLocaleString('ko-KR')}
            label={{ value: '만원/㎡', angle: -90, position: 'insideLeft', fontSize: 11 }}
          />
          <Tooltip formatter={(value) => [`${Number(value).toLocaleString('ko-KR')}만원/㎡`, '평균 단가']} />
          <Line type="monotone" dataKey="avgPricePerArea" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
