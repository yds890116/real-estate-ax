import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { RiskCategory } from '../types'

function contributionColor(score: number): string {
  if (score >= 66) return 'var(--grade-danger)'
  if (score >= 33) return 'var(--grade-caution)'
  return 'var(--grade-safe)'
}

export function RiskCategoryChart({ categories }: { categories: RiskCategory[] }) {
  const data = categories.map((c) => ({
    name: `${c.label} (${Math.round(c.weight * 100)}%)`,
    contribution: c.contribution,
    normalized: c.normalized_score,
  }))

  return (
    <ResponsiveContainer width="100%" height={Math.max(140, data.length * 36)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11 }} label={{ value: '종합점수 기여도(점)', position: 'insideBottom', offset: -2, fontSize: 11 }} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={110} />
        <Tooltip
          formatter={(value, key) =>
            key === 'contribution' ? [`${Number(value).toFixed(1)}점`, '기여도'] : [`${Number(value).toFixed(1)}점`, '카테고리 점수(0~100)']
          }
        />
        <Bar dataKey="contribution" radius={[0, 4, 4, 0]}>
          {data.map((d) => (
            <Cell key={d.name} fill={contributionColor(d.normalized)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
