import type { ListingSearchResult } from '../types'
import { formatManwon } from '../utils/format'

interface Props {
  listings: ListingSearchResult
  onScrape: () => void
  scraping: boolean
  scrapeError: string | null
}

function formatListingPrice(item: ListingSearchResult['listings'][number]): string {
  if (item.trade_type === '매매') return formatManwon(item.price)
  if (item.trade_type === '전세') return `전세 ${formatManwon(item.price)}`
  return `월세 보증금 ${formatManwon(item.price)} / 월 ${item.monthly_rent?.toLocaleString('ko-KR')}만원`
}

export function ListingsCard({ listings, onScrape, scraping, scrapeError }: Props) {
  const isLive = listings.source === 'naver_scrape'

  return (
    <section className="card">
      <div className="card-header">
        <h2>네이버 부동산 매물</h2>
        <span className={`badge ${isLive ? 'badge-ml' : 'badge-rule'}`}>{isLive ? '실시간 수집' : '샘플 데이터'}</span>
      </div>

      <p className="hint">
        기준 평형 {listings.reference_area}㎡ (단지 내 최소 평형) · {listings.complex_name}
      </p>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>거래유형</th>
              <th>전용면적</th>
              <th>층</th>
              <th>가격</th>
              <th>중개사</th>
            </tr>
          </thead>
          <tbody>
            {listings.listings.map((item) => (
              <tr key={item.id}>
                <td>
                  <span className={`badge ${item.trade_type === '매매' ? 'badge-ml' : 'badge-rule'}`}>
                    {item.trade_type}
                  </span>
                </td>
                <td>{item.exclusive_area.toFixed(2)}㎡</td>
                <td>{item.floor}</td>
                <td>{formatListingPrice(item)}</td>
                <td>{item.realtor ?? '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="opinion-actions">
        <button type="button" className="secondary-button" onClick={onScrape} disabled={scraping}>
          {scraping ? '네이버 부동산에서 수집 중...' : '실시간 매물 다시 수집'}
        </button>
      </div>

      {scrapeError && <div className="error-banner">⚠ {scrapeError}</div>}

      <p className="disclaimer">⚠ {listings.notice}</p>
    </section>
  )
}
