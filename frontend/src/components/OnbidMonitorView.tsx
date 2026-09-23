import { useEffect, useState } from 'react'
import { ApiError, getOnbidDailyItems, listOnbidCollectionDates } from '../api/client'
import type { DailyCollectionSummary, OnbidAuctionItemResponse } from '../types'
import { gradeColorClass } from '../utils/risk'
import { CourtAuctionMonitorSection } from './CourtAuctionMonitorSection'

function formatWon(amount: number | null): string {
  if (amount == null) return '-'
  const eok = Math.floor(amount / 100000000)
  const man = Math.round((amount % 100000000) / 10000)
  if (eok > 0 && man > 0) return `${eok}억 ${man.toLocaleString('ko-KR')}만원`
  if (eok > 0) return `${eok}억원`
  if (man > 0) return `${man.toLocaleString('ko-KR')}만원`
  return `${amount.toLocaleString('ko-KR')}원`
}

function formatDateLabel(dateStr: string): string {
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', weekday: 'short' })
}

export function OnbidMonitorView() {
  const [dates, setDates] = useState<DailyCollectionSummary[]>([])
  const [datesLoading, setDatesLoading] = useState(true)
  const [datesError, setDatesError] = useState<string | null>(null)

  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [items, setItems] = useState<OnbidAuctionItemResponse[]>([])
  const [itemsLoading, setItemsLoading] = useState(false)
  const [itemsError, setItemsError] = useState<string | null>(null)

  useEffect(() => {
    setDatesLoading(true)
    setDatesError(null)
    listOnbidCollectionDates(30)
      .then((list) => {
        setDates(list)
        if (list.length > 0) setSelectedDate((prev) => prev || list[0].collected_date)
      })
      .catch((e) => setDatesError(e instanceof ApiError ? e.message : '수집 일자 목록을 불러오지 못했습니다.'))
      .finally(() => setDatesLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedDate) return
    setItemsLoading(true)
    setItemsError(null)
    getOnbidDailyItems(selectedDate)
      .then((res) => setItems(res.items))
      .catch((e) => setItemsError(e instanceof ApiError ? e.message : '해당 일자의 물건 목록을 불러오지 못했습니다.'))
      .finally(() => setItemsLoading(false))
  }, [selectedDate])

  return (
    <div className="search-view">
      <CourtAuctionMonitorSection />

      <section className="card">
        <div className="card-header">
          <h2>온비드 공매 물건 모니터링</h2>
          <span className="hint">온비드(공매) 신규 등록 물건을 일자별로 수집한 내역입니다</span>
        </div>

        {datesLoading && <div className="placeholder">수집 일자를 불러오는 중입니다...</div>}
        {datesError && <div className="error-banner">⚠ {datesError}</div>}

        {!datesLoading && !datesError && (
          <div className="onbid-date-list">
            {dates.map((d) => (
              <button
                key={d.collected_date}
                type="button"
                className={`onbid-date-chip ${selectedDate === d.collected_date ? 'onbid-date-chip-active' : ''}`}
                onClick={() => setSelectedDate(d.collected_date)}
              >
                <span>{formatDateLabel(d.collected_date)}</span>
                <span className="onbid-date-chip-count">{d.item_count}건</span>
              </button>
            ))}
            {dates.length === 0 && (
              <span className="hint">
                최근 수집 내역이 없습니다. (현재 환경에서 온비드 공개 API 서버로의 네트워크 접속이 차단되어 있어
                실제 수집에 실패한 상태입니다 - 더 이상 샘플 데이터로 대체하지 않습니다.)
              </span>
            )}
          </div>
        )}
      </section>

      {itemsLoading && <div className="placeholder">물건 목록을 불러오는 중입니다...</div>}
      {itemsError && <div className="error-banner">⚠ {itemsError}</div>}

      {!itemsLoading && !itemsError && selectedDate && (
        <section className="card">
          <div className="card-header">
            <h2>{formatDateLabel(selectedDate)} 신규 등록 물건 ({items.length}건)</h2>
          </div>
          {items.length === 0 ? (
            <div className="empty-state">해당 일자에 등록된 물건이 없습니다.</div>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>물건명</th>
                    <th>용도</th>
                    <th>소재지</th>
                    <th>처분방식</th>
                    <th>감정가</th>
                    <th>최저입찰가</th>
                    <th>입찰가율</th>
                    <th>유찰횟수</th>
                    <th>상태</th>
                    <th>담보 스코어</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.cltr_nm ?? '-'}</td>
                      <td>{item.ctgr_full_nm ?? '-'}</td>
                      <td>{item.ldnm_adrs ?? item.nmrd_adrs ?? '-'}</td>
                      <td>{item.dpsl_mtd_nm ?? '-'}</td>
                      <td>{formatWon(item.appraisal_amt ?? item.apsl_ases_avg_amt)}</td>
                      <td>{formatWon(item.min_bid_prc)}</td>
                      <td>{item.fee_rate ? `${item.fee_rate}%` : '-'}</td>
                      <td>{item.uscbd_cnt ?? 0}회</td>
                      <td>{item.pbct_cltr_stat_nm ?? '-'}</td>
                      <td>
                        {item.score ? (
                          <div className="onbid-score-cell">
                            <span className={`risk-grade-badge-sm ${gradeColorClass(item.score.grade)}`}>
                              {item.score.grade}
                            </span>
                            <span className="onbid-score-label">{item.score.grade_label}</span>
                            <span className={`badge ${item.score.method === 'ml' ? 'badge-ml' : 'badge-rule'}`}>
                              {item.score.method === 'ml' ? 'ML' : '규칙'}
                            </span>
                          </div>
                        ) : (
                          '-'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {items.some((i) => i.appraisal_org_nm) && (
            <p className="disclaimer" style={{ marginTop: 12 }}>
              ⚠ 감정가·감정평가일자·감정평가업체는 온비드 감정평가 상세 정보 API 연동 결과이며, 참고용 추정치이므로 실제 감정평가와 차이가 있을 수 있습니다.
            </p>
          )}
        </section>
      )}
    </div>
  )
}
