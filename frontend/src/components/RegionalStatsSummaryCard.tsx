import type { RegionalBidStatSummary } from '../types'
import { formatManwon } from '../utils/format'

export function RegionalStatsSummaryCard({ summary }: { summary: RegionalBidStatSummary }) {
  const { latest } = summary

  return (
    <section className="card">
      <div className="card-header">
        <h2>지역 입찰통계 요약</h2>
        <span className={`badge ${summary.is_sample_data ? 'badge-rule' : 'badge-ml'}`}>
          {summary.is_sample_data ? '샘플 데이터' : '실시간 수집'}
        </span>
      </div>

      {latest ? (
        <>
          <p className="hint">
            {summary.sido}
            {summary.sigungu ? ` ${summary.sigungu}` : ''} · {latest.period.length === 6 ? `${latest.period.slice(0, 4)}.${latest.period.slice(4, 6)}` : latest.period} 기준
          </p>
          <div className="stat-grid">
            <div>
              <span className="stat-label">입찰 건수</span>
              <span className="stat-value">{latest.bid_count?.toLocaleString('ko-KR') ?? '-'}건</span>
            </div>
            <div>
              <span className="stat-label">낙찰률</span>
              <span className="stat-value">{latest.win_rate != null ? `${latest.win_rate.toFixed(1)}%` : '-'}</span>
            </div>
            <div>
              <span className="stat-label">평균 낙찰가율</span>
              <span className="stat-value">
                {latest.avg_bid_rate_vs_appraisal != null ? `${latest.avg_bid_rate_vs_appraisal.toFixed(1)}%` : '-'}
              </span>
            </div>
          </div>
          <p className="hint">
            평균 낙찰가 {latest.avg_win_bid_amt != null ? formatManwon(latest.avg_win_bid_amt * 100) : '-'} · 경쟁률{' '}
            {latest.competition_rate != null ? `${latest.competition_rate.toFixed(2)}:1` : '-'}
          </p>
        </>
      ) : (
        <p className="empty-state">해당 지역의 입찰 통계 데이터가 없습니다.</p>
      )}

      <p className="disclaimer">⚠ {summary.notice}</p>
    </section>
  )
}
