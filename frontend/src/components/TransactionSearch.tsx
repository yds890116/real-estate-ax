import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AnalyzeTarget, MarketSearchResult, MarketTransaction, RentTransaction } from '../types'
import { formatDate, formatManwon } from '../utils/format'

interface Props {
  onSearch: (query: string, months: number) => void
  onAnalyze: (target: AnalyzeTarget) => void
  result: MarketSearchResult | null
  loading: boolean
  analyzing: boolean
  error: string | null
}

function formatRent(t: RentTransaction): string {
  if (t.contract_type === '전세') return `전세 ${formatManwon(t.deposit)}`
  return `월세 보증금 ${formatManwon(t.deposit)} / 월 ${t.monthly_rent.toLocaleString('ko-KR')}만원`
}

function toTarget(t: MarketTransaction | RentTransaction): AnalyzeTarget {
  return {
    complex_name: t.complex_name,
    exclusive_area: t.exclusive_area,
    floor: t.floor,
    build_year: t.build_year,
  }
}

export function TransactionSearch({ onSearch, onAnalyze, result, loading, analyzing, error }: Props) {
  const [query, setQuery] = useState('')
  const [months, setMonths] = useState(3)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!query.trim() || loading) return
    onSearch(query.trim(), months)
  }

  return (
    <div className="search-view">
      <form className="card" onSubmit={handleSubmit}>
        <h2>1. 실거래가 검색</h2>
        <p className="hint">
          주소 또는 아파트 단지명을 입력하면 카카오 주소검색으로 위치를 확인하고, 국토교통부 매매·전월세 실거래가를
          함께 조회합니다.
        </p>
        <div className="search-form-row">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="예: 래미안대치팰리스 또는 서울 강남구 대치동 943"
          />
          <select value={months} onChange={(e) => setMonths(Number(e.target.value))}>
            <option value={1}>최근 1개월</option>
            <option value={3}>최근 3개월</option>
            <option value={6}>최근 6개월</option>
          </select>
          <button type="submit" disabled={loading}>
            {loading ? '검색 중...' : '검색'}
          </button>
        </div>
      </form>

      {error && <div className="error-banner">⚠ {error}</div>}

      {result && (
        <>
          <div className="card">
            <div className="card-header">
              <h2>
                {result.location.sido} {result.location.sigungu} {result.location.dong ?? ''}
              </h2>
              <span className="hint">
                법정동코드 {result.location.lawd_cd} · {result.location.source === 'keyword' ? '단지명 검색' : '주소 검색'}
              </span>
            </div>
            <p className="hint">
              조회 기간 {result.months_searched[result.months_searched.length - 1]}~{result.months_searched[0]}
              {result.filter_applied ? ` · "${result.filter_applied}" 필터 적용` : ''}
            </p>
          </div>

          <div className="card">
            <div className="card-header">
              <h2>2. 국토교통부 실거래가 — 매매</h2>
              <span className="hint">
                총 {result.sale.total_fetched.toLocaleString('ko-KR')}건 중 {result.sale.total_matched}건 매치
              </span>
            </div>
            {result.sale.transactions.length === 0 ? (
              <p className="empty-state">매매 실거래가 없습니다.</p>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>거래일</th>
                      <th>단지명</th>
                      <th>전용면적</th>
                      <th>층</th>
                      <th>준공연도</th>
                      <th>거래금액</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.sale.transactions.map((t) => (
                      <tr key={t.id}>
                        <td>{formatDate(t.deal_date)}</td>
                        <td>{t.complex_name ?? '-'}</td>
                        <td>{t.exclusive_area.toFixed(2)}㎡</td>
                        <td>{t.floor ?? '-'}</td>
                        <td>{t.build_year ?? '-'}</td>
                        <td>{formatManwon(t.deal_price)}</td>
                        <td>
                          <button
                            type="button"
                            className="link-button"
                            disabled={analyzing}
                            onClick={() => onAnalyze(toTarget(t))}
                          >
                            AI 분석 →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <h2>2. 국토교통부 실거래가 — 전월세</h2>
              <span className="hint">
                총 {result.rent.total_fetched.toLocaleString('ko-KR')}건 중 {result.rent.total_matched}건 매치
              </span>
            </div>
            {result.rent.transactions.length === 0 ? (
              <p className="empty-state">전월세 실거래가 없습니다.</p>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>거래일</th>
                      <th>단지명</th>
                      <th>전용면적</th>
                      <th>층</th>
                      <th>유형</th>
                      <th>보증금/월세</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.rent.transactions.map((t) => (
                      <tr key={t.id}>
                        <td>{formatDate(t.deal_date)}</td>
                        <td>{t.complex_name ?? '-'}</td>
                        <td>{t.exclusive_area.toFixed(2)}㎡</td>
                        <td>{t.floor ?? '-'}</td>
                        <td>
                          <span className={`badge ${t.contract_type === '전세' ? 'badge-rule' : 'badge-ml'}`}>
                            {t.contract_type}
                          </span>
                        </td>
                        <td>{formatRent(t)}</td>
                        <td>
                          <button
                            type="button"
                            className="link-button"
                            disabled={analyzing}
                            onClick={() => onAnalyze(toTarget(t))}
                          >
                            AI 분석 →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
