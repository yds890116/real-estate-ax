import type { DashboardItem } from '../types'
import { formatManwon } from '../utils/format'
import { gradeColorClass } from '../utils/risk'

interface Props {
  items: DashboardItem[]
  loading: boolean
  error: string | null
  onSelect: (propertyId: number) => void
}

const OPINION_LABEL: Record<DashboardItem['opinion_status'], string> = {
  none: '미생성',
  draft: 'AI 초안',
  edited: '심사역 수정',
}

export function Dashboard({ items, loading, error, onSelect }: Props) {
  if (loading) return <div className="placeholder">대시보드를 불러오는 중입니다...</div>
  if (error) return <div className="error-banner">⚠ {error}</div>
  if (items.length === 0) {
    return <div className="placeholder">등록된 물건이 없습니다. &ldquo;종합분석&rdquo; 탭에서 물건을 먼저 등록해주세요.</div>
  }

  const alertCount = items.filter((i) => i.alerts.length > 0).length

  return (
    <div className="dashboard">
      <div className="dashboard-summary">
        <span>
          전체 <strong>{items.length}</strong>건
        </span>
        <span className={alertCount > 0 ? 'dashboard-alert-count' : ''}>
          이상 매물 <strong>{alertCount}</strong>건
        </span>
      </div>

      <div className="card">
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>주소</th>
                <th>AI 추정시세</th>
                <th>리스크</th>
                <th>참고 감정가</th>
                <th>등기부</th>
                <th>심사의견</th>
                <th>알림</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.property_id}>
                  <td>{item.address}</td>
                  <td>{formatManwon(item.estimated_price)}</td>
                  <td>
                    <span className={`risk-grade-badge-sm ${gradeColorClass(item.risk_grade)}`}>{item.risk_grade}</span>{' '}
                    {item.risk_level_label}
                  </td>
                  <td>{item.reference_price != null ? formatManwon(item.reference_price) : '-'}</td>
                  <td>{item.has_registry ? `위험요인 ${item.registry_risk_count}건` : '미업로드'}</td>
                  <td>{OPINION_LABEL[item.opinion_status]}</td>
                  <td>
                    {item.alerts.length > 0 ? (
                      <span className="alert-badge" title={item.alerts.join('\n')}>
                        ⚠ {item.alerts.length}건
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td>
                    <button type="button" className="link-button" onClick={() => onSelect(item.property_id)}>
                      상세보기
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
