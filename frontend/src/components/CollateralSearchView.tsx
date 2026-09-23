import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, createProperty, getHogangnonoPrice, getPropertyAnalysis, searchMarketTransactions } from '../api/client'
import type { AutocompleteSuggestion, HogangnonoComplexResult, MarketSearchResult, PropertyAnalysis } from '../types'
import { AutocompleteSearchBox } from './AutocompleteSearchBox'
import { CostIncomeCard } from './CostIncomeCard'
import { HeadlineEstimateCard } from './HeadlineEstimateCard'
import { HogangnonoCard } from './HogangnonoCard'
import { MolitTransactionCard } from './MolitTransactionCard'
import { RegionalTrendCard } from './RegionalTrendCard'
import { RiskCard } from './RiskCard'
import { SkeletonCard } from './SkeletonCard'

const ASSET_TYPES = ['아파트', '빌라', '오피스텔', '상가', '단독주택', '기타']
const COMPARABLE_SALE_TYPES = new Set(['아파트', '빌라'])

export function CollateralSearchView() {
  const [query, setQuery] = useState('')
  const [complexHint, setComplexHint] = useState<string | null>(null)
  const [assetType, setAssetType] = useState('아파트')
  const [exclusiveArea, setExclusiveArea] = useState('84.97')
  const [floor, setFloor] = useState('')
  const [buildYear, setBuildYear] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [molitResult, setMolitResult] = useState<MarketSearchResult | null>(null)
  const [analysis, setAnalysis] = useState<PropertyAnalysis | null>(null)

  const [hogangnonoResult, setHogangnonoResult] = useState<HogangnonoComplexResult | null>(null)
  const [hogangnonoLoading, setHogangnonoLoading] = useState(false)

  function handleSelectSuggestion(s: AutocompleteSuggestion) {
    setQuery(s.road_address_name || s.address_name)
    setComplexHint(s.place_name || null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const area = Number(exclusiveArea)
    if (!query.trim() || !area || area <= 0 || loading) return

    setLoading(true)
    setError(null)
    setAnalysis(null)
    setMolitResult(null)
    setHogangnonoResult(null)

    // 호갱노노 조회는 지도를 실제로 이동시키며 데이터를 모아 10~30초 걸릴 수 있어, 메인 분석과
    // 별도로(블로킹 없이) 돌리고 준비되는 대로 채운다.
    setHogangnonoLoading(true)
    getHogangnonoPrice(query.trim(), complexHint)
      .then(setHogangnonoResult)
      .catch(() => setHogangnonoResult(null))
      .finally(() => setHogangnonoLoading(false))

    try {
      const searchResult = await searchMarketTransactions(query.trim(), 3)
      setMolitResult(searchResult)

      const loc = searchResult.location
      // 자동완성 후보를 클릭하지 않고 바로 검색한 경우 complexHint가 비어있을 수 있다 —
      // 이때는 카카오 주소/키워드 검색이 자체적으로 추정한 단지명(건물명)으로 대체한다.
      const resolvedComplexName = complexHint || loc.complex_name_hint
      const property = await createProperty({
        address: [loc.sido, loc.sigungu, loc.dong, resolvedComplexName].filter(Boolean).join(' '),
        sido: loc.sido,
        sigungu: loc.sigungu,
        dong: loc.dong,
        property_type: assetType,
        complex_name: resolvedComplexName,
        exclusive_area: area,
        floor: floor ? Number(floor) : null,
        total_floors: null,
        build_year: buildYear ? Number(buildYear) : null,
        household_count: null,
      })

      const analysisResult = await getPropertyAnalysis(property.id)
      setAnalysis(analysisResult)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '분석 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const isComparableType = COMPARABLE_SALE_TYPES.has(assetType)

  return (
    <div className="search-view">
      <form className="card" onSubmit={handleSubmit}>
        <h2>담보 물건 검색 및 시세·등급 추정</h2>
        <p className="hint">주소 또는 아파트 단지명을 입력하면 자동완성 후보가 표시됩니다.</p>

        <div className="search-form-row">
          <AutocompleteSearchBox
            value={query}
            onChange={setQuery}
            onSelect={handleSelectSuggestion}
            placeholder="예: 래미안대치팰리스 또는 서울 강남구 대치동 943"
          />
        </div>

        <div className="collateral-form-grid">
          <label>
            자산유형
            <select value={assetType} onChange={(e) => setAssetType(e.target.value)}>
              {ASSET_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label>
            전용면적(㎡)
            <input type="number" step="0.01" value={exclusiveArea} onChange={(e) => setExclusiveArea(e.target.value)} required />
          </label>
          <label>
            층
            <input type="number" value={floor} onChange={(e) => setFloor(e.target.value)} placeholder="선택" />
          </label>
          <label>
            준공연도
            <input type="number" value={buildYear} onChange={(e) => setBuildYear(e.target.value)} placeholder="선택" />
          </label>
        </div>

        <div className="opinion-actions">
          <button type="submit" disabled={loading}>
            {loading ? '분석 중...' : '종합분석 조회'}
          </button>
        </div>
      </form>

      {error && <div className="error-banner">⚠ {error}</div>}

      {loading && (
        <>
          <SkeletonCard lines={4} />
          <SkeletonCard lines={3} />
          <SkeletonCard lines={3} />
          <SkeletonCard hero lines={2} />
          <SkeletonCard lines={5} />
        </>
      )}

      {!loading && analysis && (
        <>
          <div className="ai-draft-banner">🤖 AI 참고 분석 결과 — 심사역 검토 전 초안입니다.</div>

          {isComparableType ? (
            molitResult && <MolitTransactionCard result={molitResult} />
          ) : (
            analysis.cost_income_estimate && <CostIncomeCard estimate={analysis.cost_income_estimate} />
          )}

          {(hogangnonoLoading || hogangnonoResult) && <HogangnonoCard result={hogangnonoResult} loading={hogangnonoLoading} />}

          {analysis.regional_trend && <RegionalTrendCard trend={analysis.regional_trend} />}

          <HeadlineEstimateCard
            valuation={analysis.valuation}
            costIncome={analysis.cost_income_estimate}
            molit={molitResult}
            regionalTrend={analysis.regional_trend}
            hogangnono={hogangnonoResult}
          />

          <RiskCard risk={analysis.risk} />
        </>
      )}
    </div>
  )
}
