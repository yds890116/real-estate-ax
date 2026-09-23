import type { HogangnonoComplexResult, HogangnonoListingItem } from '../types'
import { formatManwon } from '../utils/format'

interface Props {
  result: HogangnonoComplexResult | null
  loading: boolean
}

function tradeTypeBadgeClass(tradeType: HogangnonoListingItem['trade_type']): string {
  if (tradeType === '매매') return 'badge-ml'
  if (tradeType === '전세') return 'badge-rule'
  return 'badge-warning'
}

function formatListingPrice(item: HogangnonoListingItem): string {
  if (item.trade_type === '월세' && item.monthly_rent != null) {
    return `${formatManwon(item.price)} / 월 ${item.monthly_rent.toLocaleString('ko-KR')}만원`
  }
  return formatManwon(item.price)
}

export function HogangnonoCard({ result, loading }: Props) {
  if (loading) {
    return (
      <section className="card skeleton-card" aria-busy="true">
        <div className="skeleton-block skeleton-title" />
        <div className="skeleton-block skeleton-line" />
        <div className="skeleton-block skeleton-line short" />
        <p className="hint" style={{ marginTop: 8 }}>
          호갱노노에서 실시간 시세를 조회하는 중입니다 (지도 이동까지 포함해 10~30초 정도 걸릴 수 있어요)...
        </p>
      </section>
    )
  }

  if (!result || !result.found) {
    return (
      <section className="card">
        <h2>호갱노노 실거래가</h2>
        <p className="empty-state">{result?.notice ?? '호갱노노에서 단지를 찾지 못했습니다.'}</p>
      </section>
    )
  }

  return (
    <section className="card">
      <div className="card-header">
        <h2>호갱노노 실거래가</h2>
        <span className="badge badge-ml">실시간 수집</span>
      </div>

      <p className="hint">
        {result.complex_name} · {result.road_address ?? result.address} · {result.total_household?.toLocaleString('ko-KR')}세대
      </p>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>전용면적</th>
              <th>실거래가(매매)</th>
              <th>실거래가(전세)</th>
            </tr>
          </thead>
          <tbody>
            {result.areas.map((a) => (
              <tr key={a.area_no}>
                <td>{a.private_area.toFixed(2)}㎡</td>
                <td>{a.real_trade_price != null ? formatManwon(a.real_trade_price) : '-'}</td>
                <td>{a.real_rent_price != null ? formatManwon(a.real_rent_price) : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: 20 }}>호갱노노 매물 ({result.listings.length}건)</h2>
      {result.listings.length === 0 ? (
        <p className="empty-state">현재 등록된 매물이 없습니다.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>거래유형</th>
                <th>전용면적</th>
                <th>가격</th>
                <th>동</th>
                <th>층</th>
                <th>타입</th>
                <th>설명</th>
              </tr>
            </thead>
            <tbody>
              {result.listings.map((item) => (
                <tr key={item.item_id}>
                  <td>
                    <span className={`badge ${tradeTypeBadgeClass(item.trade_type)}`}>{item.trade_type}</span>
                  </td>
                  <td>{item.private_area.toFixed(2)}㎡</td>
                  <td>{formatListingPrice(item)}</td>
                  <td>{item.dong_name ?? '-'}</td>
                  <td>{item.floor_tier ?? '-'}</td>
                  <td>{item.room_type ?? '-'}</td>
                  <td style={{ whiteSpace: 'normal', minWidth: 220 }}>{item.title ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="disclaimer" style={{ marginTop: 12 }}>⚠ {result.notice}</p>
    </section>
  )
}
