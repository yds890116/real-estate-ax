import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ListingComparison } from '../types'
import { TrendTag } from './TrendTag'

function gapColor(gapRatio: number | null): string {
  if (gapRatio == null) return 'var(--text-secondary)'
  if (gapRatio > 5) return 'var(--grade-warning)'
  if (gapRatio < -5) return 'var(--accent)'
  return 'var(--grade-safe)'
}

export function ListingComparisonCard({ comparison }: { comparison: ListingComparison }) {
  const data = [
    { name: '최근 실거래가', unitPrice: comparison.market_unit_price ?? 0 },
    { name: '매물 호가', unitPrice: comparison.listing_unit_price ?? 0 },
  ]

  return (
    <section className="card">
      <div className="card-header">
        <h2>실거래가 vs 매물호가 비교</h2>
        <TrendTag value={comparison.gap_ratio} decimals={1} />
      </div>

      <p className="hint">
        기준 평형 {comparison.reference_area}㎡ · 실거래 {comparison.market_transaction_count}건 · 매물(매매)
        {comparison.listing_count}건
      </p>

      {comparison.market_unit_price != null && comparison.listing_unit_price != null ? (
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 32, left: 8, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('ko-KR')} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={90} />
            <Tooltip formatter={(value) => [`${Number(value).toLocaleString('ko-KR')}만원/㎡`, '단가']} />
            <Bar dataKey="unitPrice" radius={[0, 4, 4, 0]}>
              <Cell fill="var(--accent)" />
              <Cell fill={gapColor(comparison.gap_ratio)} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p className="empty-state">비교할 매매 매물 또는 실거래가가 부족합니다.</p>
      )}

      <p className="registry-summary">{comparison.explanation}</p>
    </section>
  )
}
