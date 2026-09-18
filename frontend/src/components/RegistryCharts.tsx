import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { RegistryRight } from '../types'
import { formatManwon } from '../utils/format'

const RISK_TYPES = new Set(['가압류', '가처분', '압류', '가등기', '임의경매개시결정', '강제경매개시결정'])

interface Props {
  rights: RegistryRight[]
  mortgageTotal: number | null
  estimatedPrice: number | null
}

function ratioColor(ratio: number): string {
  if (ratio >= 0.7) return 'var(--grade-danger)'
  if (ratio >= 0.5) return 'var(--grade-caution)'
  return 'var(--grade-safe)'
}

export function RegistryCharts({ rights, mortgageTotal, estimatedPrice }: Props) {
  const mortgageData = useMemo(
    () =>
      rights
        .filter((r) => r.right_type.startsWith('근저당권설정') && r.amount != null)
        .map((r, i) => ({
          name: r.holder ?? `근저당권 ${i + 1}`,
          amount: r.amount as number,
          date: r.registered_date ?? '일자 미상',
        })),
    [rights],
  )

  const typeData = useMemo(() => {
    const counts = new Map<string, number>()
    for (const r of rights) counts.set(r.right_type, (counts.get(r.right_type) ?? 0) + 1)
    return Array.from(counts.entries())
      .map(([type, count]) => ({ type, count, risky: RISK_TYPES.has(type) }))
      .sort((a, b) => b.count - a.count)
  }, [rights])

  const ratio = mortgageTotal != null && estimatedPrice ? mortgageTotal / estimatedPrice : null

  if (rights.length === 0) return null

  return (
    <section className="card">
      <h2>3. 권리분석 상세 (그래프)</h2>

      {ratio != null && mortgageTotal != null && estimatedPrice != null && (
        <div className="ltv-gauge">
          <div className="ltv-gauge-label">
            <span>근저당권 합계 {formatManwon(mortgageTotal)}</span>
            <span>AI 추정시세 {formatManwon(estimatedPrice)}</span>
          </div>
          <div className="ltv-gauge-track">
            <div
              className="ltv-gauge-fill"
              style={{ width: `${Math.min(ratio * 100, 100)}%`, background: ratioColor(ratio) }}
            />
          </div>
          <p className="hint">근저당권 합계가 추정시세의 {(ratio * 100).toFixed(0)}%입니다 (70% 이상이면 담보여력 부족 우려).</p>
        </div>
      )}

      {mortgageData.length > 0 && (
        <>
          <p className="opinion-label">근저당권 채권최고액 구성</p>
          <ResponsiveContainer width="100%" height={Math.max(120, mortgageData.length * 50)}>
            <BarChart data={mortgageData} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('ko-KR')} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={120} />
              <Tooltip
                formatter={(value) => [`${Number(value).toLocaleString('ko-KR')}만원`, '채권최고액']}
                labelFormatter={(label, payload) => `${label} (${payload?.[0]?.payload?.date ?? ''})`}
              />
              <Bar dataKey="amount" fill="var(--accent)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}

      <p className="opinion-label">권리유형별 건수</p>
      <ResponsiveContainer width="100%" height={Math.max(120, typeData.length * 34)}>
        <BarChart data={typeData} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="type" tick={{ fontSize: 12 }} width={120} />
          <Tooltip formatter={(value) => [`${Number(value)}건`, '건수']} />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {typeData.map((d) => (
              <Cell key={d.type} fill={d.risky ? 'var(--grade-warning)' : 'var(--accent)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </section>
  )
}
