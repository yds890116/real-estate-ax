import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ApiError, getCollateralScoreModelInfo, trainCollateralScoreModel } from '../api/client'
import type { CollateralScoreModelInfo } from '../types'

function formatDateTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const BAR_COLORS = ['#2f6fed', '#5b8def', '#7aa5f0', '#9bbdf3', '#bcd4f6', '#dcebfa']

export function ScoringModelView() {
  const [info, setInfo] = useState<CollateralScoreModelInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [training, setTraining] = useState(false)
  const [trainError, setTrainError] = useState<string | null>(null)

  function loadInfo() {
    setLoading(true)
    setError(null)
    return getCollateralScoreModelInfo()
      .then(setInfo)
      .catch((e) => setError(e instanceof ApiError ? e.message : '모델 정보를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadInfo()
  }, [])

  async function handleRetrain() {
    setTraining(true)
    setTrainError(null)
    try {
      await trainCollateralScoreModel()
      await loadInfo()
    } catch (e) {
      setTrainError(e instanceof ApiError ? e.message : '재학습 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setTraining(false)
    }
  }

  const importanceData = info
    ? Object.entries(info.feature_importances)
        .sort((a, b) => b[1] - a[1])
        .map(([key, value]) => ({
          key,
          label: info.feature_descriptions[key] ?? key,
          value: Math.round(value * 1000) / 10,
        }))
    : []

  const sourceEntries = info ? Object.entries(info.source_breakdown) : []
  const totalRows = sourceEntries.reduce((sum, [, count]) => sum + count, 0)

  return (
    <div className="search-view">
      <section className="card">
        <div className="card-header">
          <h2>담보 스코어링 모델 투명성</h2>
          <span className="hint">경매·공매 낙찰 이력 기반으로 학습된 담보물건 리스크 스코어링 모델입니다</span>
        </div>

        {loading && <div className="placeholder">모델 정보를 불러오는 중입니다...</div>}
        {error && <div className="error-banner">⚠ {error}</div>}

        {!loading && !error && info && (
          <>
            <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
              <div>
                <span className="stat-label">모델 상태</span>
                <span className="stat-value">{info.is_available ? '학습 완료' : '미학습'}</span>
              </div>
              <div>
                <span className="stat-label">학습 데이터 건수</span>
                <span className="stat-value">{info.n_rows.toLocaleString('ko-KR')}건</span>
              </div>
              <div>
                <span className="stat-label">최근 학습일시</span>
                <span className="stat-value">{formatDateTime(info.trained_at)}</span>
              </div>
              <div>
                <span className="stat-label">결정계수(R²)</span>
                <span className="stat-value">{info.metrics.r2 != null ? info.metrics.r2.toFixed(3) : '-'}</span>
              </div>
            </div>

            <div className="onbid-source-breakdown">
              {sourceEntries.map(([source, count]) => (
                <span key={source} className={`badge ${source === 'sample' ? 'badge-rule' : 'badge-ml'}`}>
                  {source === 'sample' ? '샘플 데이터' : source} {count.toLocaleString('ko-KR')}건
                  {totalRows > 0 ? ` (${Math.round((count / totalRows) * 100)}%)` : ''}
                </span>
              ))}
            </div>

            <div className="button-row" style={{ marginTop: 14 }}>
              <button type="button" onClick={handleRetrain} disabled={training}>
                {training ? '재학습 중...' : '지금 재학습'}
              </button>
            </div>
            {trainError && <div className="error-banner" style={{ marginTop: 10 }}>⚠ {trainError}</div>}

            <p className="disclaimer" style={{ marginTop: 14 }}>
              ⚠ {info.target_description}
            </p>
          </>
        )}
      </section>

      {!loading && !error && info && (
        <section className="card">
          <div className="card-header">
            <h2>성능 지표</h2>
          </div>
          <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
            <div>
              <span className="stat-label">MAE (평균절대오차)</span>
              <span className="stat-value">{info.metrics.mae != null ? info.metrics.mae.toFixed(3) : '-'}</span>
            </div>
            <div>
              <span className="stat-label">RMSE (평균제곱근오차)</span>
              <span className="stat-value">{info.metrics.rmse != null ? info.metrics.rmse.toFixed(3) : '-'}</span>
            </div>
            <div>
              <span className="stat-label">R² (결정계수)</span>
              <span className="stat-value">{info.metrics.r2 != null ? info.metrics.r2.toFixed(3) : '-'}</span>
            </div>
          </div>
        </section>
      )}

      {!loading && !error && info && importanceData.length > 0 && (
        <section className="card">
          <div className="card-header">
            <h2>Feature Importance (예측 기여도)</h2>
            <span className="hint">유찰횟수 예측에 각 데이터 항목이 기여한 비중(%)</span>
          </div>
          <ResponsiveContainer width="100%" height={Math.max(180, importanceData.length * 44)}>
            <BarChart data={importanceData} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 12 }} unit="%" />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 12 }} width={180} />
              <Tooltip formatter={(value) => [`${value}%`, '기여도']} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {importanceData.map((entry, idx) => (
                  <Cell key={entry.key} fill={BAR_COLORS[idx % BAR_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      {!loading && !error && info && (
        <section className="card">
          <div className="card-header">
            <h2>학습에 사용된 데이터 항목</h2>
          </div>
          <ul className="factor-list">
            {Object.entries(info.feature_descriptions).map(([key, desc]) => (
              <li key={key} className="factor-item">
                <strong>{desc}</strong>
                <span className="hint" style={{ marginLeft: 8 }}>
                  {key}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
