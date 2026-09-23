import type { MarketSearchResult } from '../types'
import { formatDate, formatManwon } from '../utils/format'

export function MolitTransactionCard({ result }: { result: MarketSearchResult }) {
  return (
    <section className="card">
      <div className="card-header">
        <h2>국토교통부 매매·전월세 실거래가</h2>
        <span className="hint">
          {result.location.sido} {result.location.sigungu} {result.location.dong ?? ''} · 최근 {result.months_searched.length}개월
        </span>
      </div>

      <p className="opinion-label">매매 ({result.sale.total_matched}건)</p>
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
                <th>거래금액</th>
              </tr>
            </thead>
            <tbody>
              {result.sale.transactions.slice(0, 8).map((t) => (
                <tr key={t.id}>
                  <td>{formatDate(t.deal_date)}</td>
                  <td>{t.complex_name ?? '-'}</td>
                  <td>{t.exclusive_area.toFixed(2)}㎡</td>
                  <td>{t.floor ?? '-'}</td>
                  <td>{formatManwon(t.deal_price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="opinion-label" style={{ marginTop: 14 }}>
        전월세 ({result.rent.total_matched}건)
      </p>
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
                <th>유형</th>
                <th>보증금/월세</th>
              </tr>
            </thead>
            <tbody>
              {result.rent.transactions.slice(0, 8).map((t) => (
                <tr key={t.id}>
                  <td>{formatDate(t.deal_date)}</td>
                  <td>{t.complex_name ?? '-'}</td>
                  <td>{t.exclusive_area.toFixed(2)}㎡</td>
                  <td>
                    <span className={`badge ${t.contract_type === '전세' ? 'badge-rule' : 'badge-ml'}`}>{t.contract_type}</span>
                  </td>
                  <td>
                    {t.contract_type === '전세'
                      ? formatManwon(t.deposit)
                      : `보증금 ${formatManwon(t.deposit)} / 월 ${t.monthly_rent.toLocaleString('ko-KR')}만원`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
