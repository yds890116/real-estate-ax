import type { RegistryAnalysisResult } from '../types'
import { formatManwon } from '../utils/format'

export function RegistryCard({ registry }: { registry: RegistryAnalysisResult }) {
  const isLlm = registry.generation_method === 'llm'

  return (
    <section className="card">
      <div className="card-header">
        <h2>2. 권리관계 요약</h2>
        <span className={`badge ${isLlm ? 'badge-ml' : 'badge-rule'}`}>{isLlm ? 'Claude 생성' : '템플릿 생성'}</span>
      </div>

      <p className="registry-summary">{registry.summary}</p>

      <ul className="risk-flag-list">
        {registry.risk_flags.map((flag) => (
          <li key={flag}>{flag}</li>
        ))}
      </ul>

      {registry.rights.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>구분</th>
                <th>권리유형</th>
                <th>권리자</th>
                <th>금액</th>
                <th>등기일</th>
              </tr>
            </thead>
            <tbody>
              {registry.rights.map((r, i) => (
                <tr key={i}>
                  <td>{r.section}</td>
                  <td>{r.right_type}</td>
                  <td>{r.holder ?? '-'}</td>
                  <td>{r.amount != null ? formatManwon(r.amount) : '-'}</td>
                  <td>{r.registered_date ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="disclaimer">⚠ {registry.disclaimer}</p>
    </section>
  )
}
