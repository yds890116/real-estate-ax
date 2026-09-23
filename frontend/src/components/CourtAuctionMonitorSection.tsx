import { useEffect, useState } from 'react'
import { ApiError, collectCourtAuctionNow, getCourtAuctionDailyItems, listCourtAuctionCollectionDates } from '../api/client'
import type { CourtAuctionDailyCollectionSummary, CourtAuctionItemResponse } from '../types'

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

function formatSaleDate(ymd: string | null): string {
  if (!ymd || ymd.length !== 8) return '-'
  return `${ymd.slice(0, 4)}.${ymd.slice(4, 6)}.${ymd.slice(6, 8)}`
}

export function CourtAuctionMonitorSection() {
  const [dates, setDates] = useState<CourtAuctionDailyCollectionSummary[]>([])
  const [datesLoading, setDatesLoading] = useState(true)
  const [datesError, setDatesError] = useState<string | null>(null)

  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [items, setItems] = useState<CourtAuctionItemResponse[]>([])
  const [itemsLoading, setItemsLoading] = useState(false)
  const [itemsError, setItemsError] = useState<string | null>(null)

  const [collecting, setCollecting] = useState(false)
  const [collectError, setCollectError] = useState<string | null>(null)
  const [collectResultMsg, setCollectResultMsg] = useState<string | null>(null)

  function loadDates() {
    setDatesLoading(true)
    setDatesError(null)
    return listCourtAuctionCollectionDates(30)
      .then((list) => {
        setDates(list)
        if (list.length > 0) setSelectedDate((prev) => prev || list[0].collected_date)
      })
      .catch((e) => setDatesError(e instanceof ApiError ? e.message : '수집 일자 목록을 불러오지 못했습니다.'))
      .finally(() => setDatesLoading(false))
  }

  useEffect(() => {
    loadDates()
  }, [])

  useEffect(() => {
    if (!selectedDate) return
    setItemsLoading(true)
    setItemsError(null)
    getCourtAuctionDailyItems(selectedDate)
      .then((res) => setItems(res.items))
      .catch((e) => setItemsError(e instanceof ApiError ? e.message : '해당 일자의 물건 목록을 불러오지 못했습니다.'))
      .finally(() => setItemsLoading(false))
  }, [selectedDate])

  async function handleCollectNow() {
    setCollecting(true)
    setCollectError(null)
    setCollectResultMsg(null)
    try {
      const result = await collectCourtAuctionNow()
      setCollectResultMsg(`신규 ${result.collected}건 수집(중복 ${result.skipped}건 제외)`)
      await loadDates()
      if (selectedDate) {
        const res = await getCourtAuctionDailyItems(selectedDate)
        setItems(res.items)
      }
    } catch (e) {
      setCollectError(e instanceof ApiError ? e.message : '수집 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setCollecting(false)
    }
  }

  return (
    <>
      <section className="card">
        <div className="card-header">
          <h2>법원경매 신규 매각공고</h2>
          <span className="hint">
            대한민국 법원 법원경매정보(courtauction.go.kr)에서 실시간 수집한 매각기일 기준 물건입니다
          </span>
        </div>

        <div className="button-row">
          <button type="button" onClick={handleCollectNow} disabled={collecting}>
            {collecting ? '수집 중... (1~2분 소요될 수 있어요)' : '지금 수집'}
          </button>
        </div>
        {collectResultMsg && (
          <p className="hint" style={{ marginTop: 8 }}>
            ✅ {collectResultMsg}
          </p>
        )}
        {collectError && (
          <div className="error-banner" style={{ marginTop: 8 }}>
            ⚠ {collectError}
          </div>
        )}

        {datesLoading && <div className="placeholder">수집 일자를 불러오는 중입니다...</div>}
        {datesError && <div className="error-banner">⚠ {datesError}</div>}

        {!datesLoading && !datesError && (
          <div className="onbid-date-list" style={{ marginTop: 12 }}>
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
              <span className="hint">아직 수집된 물건이 없습니다. 위 "지금 수집" 버튼을 눌러보세요.</span>
            )}
          </div>
        )}
      </section>

      {itemsLoading && <div className="placeholder">물건 목록을 불러오는 중입니다...</div>}
      {itemsError && <div className="error-banner">⚠ {itemsError}</div>}

      {!itemsLoading && !itemsError && selectedDate && (
        <section className="card">
          <div className="card-header">
            <h2>{formatDateLabel(selectedDate)} 신규 매각공고 ({items.length}건)</h2>
          </div>
          {items.length === 0 ? (
            <div className="empty-state">해당 일자에 수집된 물건이 없습니다.</div>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>사건번호</th>
                    <th>법원</th>
                    <th>물건종류</th>
                    <th>소재지</th>
                    <th>감정가</th>
                    <th>최저매각가</th>
                    <th>매각가율</th>
                    <th>매각기일</th>
                    <th>진행상태</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        {item.case_no}
                        {item.item_no ? ` (${item.item_no})` : ''}
                      </td>
                      <td>{item.court_name ?? '-'}</td>
                      <td>{item.usage_name ?? '-'}</td>
                      <td>{item.address ?? '-'}</td>
                      <td>{formatWon(item.appraisal_amt)}</td>
                      <td>{formatWon(item.min_sale_price)}</td>
                      <td>{item.min_sale_price_rate ? `${item.min_sale_price_rate}%` : '-'}</td>
                      <td>{formatSaleDate(item.sale_date)}</td>
                      <td>{item.status ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="disclaimer" style={{ marginTop: 12 }}>
            ⚠ 법원경매정보 공개 데이터를 참고용으로 정리한 것이며, 실제 입찰 전 법원 물건명세서·현황조사보고서·감정평가서를 반드시 재확인해야 합니다.
          </p>
        </section>
      )}
    </>
  )
}
