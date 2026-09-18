import type { AppraisalSearchResult } from '../types'
import { formatManwon } from '../utils/format'

export function AppraisalCard({ appraisal }: { appraisal: AppraisalSearchResult }) {
  const isLlm = appraisal.generation_method === 'llm'

  return (
    <section className="card">
      <div className="card-header">
        <h2>유사 감정평가·거래사례</h2>
        <span className={`badge ${isLlm ? 'badge-ml' : 'badge-rule'}`}>{isLlm ? 'Claude 생성' : '템플릿 생성'}</span>
      </div>

      {appraisal.reference_price != null ? (
        <>
          <p className="valuation-price">{formatManwon(appraisal.reference_price)}</p>
          <p className="valuation-range">
            {appraisal.reference_area != null
              ? `단지 내 최소 평형(${appraisal.reference_area}㎡) 최근 실거래 기준`
              : `유사사례 가중평균 단가 ${appraisal.reference_price_per_area?.toLocaleString('ko-KR')}만원/㎡ 기준 참고 감정가`}
          </p>
        </>
      ) : (
        <p className="empty-state">조건에 맞는 유사사례를 찾지 못했습니다.</p>
      )}

      <p className="registry-summary">{appraisal.explanation}</p>

      {appraisal.cases.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>구분</th>
                <th>소재지</th>
                <th>용도</th>
                <th>면적</th>
                <th>단가</th>
                <th>일자</th>
                <th>유사도</th>
              </tr>
            </thead>
            <tbody>
              {appraisal.cases.map((c) => (
                <tr key={c.id}>
                  <td>{c.case_type}</td>
                  <td>
                    {c.dong} {c.complex_name}
                  </td>
                  <td>{c.usage}</td>
                  <td>{c.exclusive_area.toFixed(2)}㎡</td>
                  <td>{c.unit_price.toLocaleString('ko-KR')}만원/㎡</td>
                  <td>{c.event_date}</td>
                  <td>{c.similarity != null ? `${Math.round(c.similarity * 100)}%` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="disclaimer">⚠ {appraisal.disclaimer}</p>
    </section>
  )
}
