import { Area, AreaChart, ResponsiveContainer, Tooltip } from 'recharts'

interface Point {
  label: string
  value: number
}

export function Sparkline({ data, height = 56, formatValue }: { data: Point[]; height?: number; formatValue?: (v: number) => string }) {
  if (data.length < 2) return null

  const last = data[data.length - 1].value
  const first = data[0].value
  const trendUp = last >= first
  const color = trendUp ? 'var(--grade-danger)' : 'var(--grade-safe)'

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="sparklineFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Tooltip
          cursor={false}
          contentStyle={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            fontSize: 11,
            padding: '4px 8px',
          }}
          labelStyle={{ color: 'var(--text-secondary)' }}
          itemStyle={{ color: 'var(--text-primary)' }}
          formatter={(value: number) => [formatValue ? formatValue(value) : value.toLocaleString('ko-KR'), '']}
          labelFormatter={(label) => label}
        />
        <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2} fill="url(#sparklineFill)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
