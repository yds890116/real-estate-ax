import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  analyzeRegistry,
  ApiError,
  createProperty,
  getDashboard,
  getHogangnonoPrice,
  getPropertyAnalysis,
  searchMarketTransactions,
} from '../api/client'
import type {
  AutocompleteSuggestion,
  DashboardItem,
  HogangnonoComplexResult,
  MarketSearchResult,
  PropertyAnalysis,
  RegistryAnalysisResult,
} from '../types'
import { AppraisalCard } from './AppraisalCard'
import { CostIncomeCard } from './CostIncomeCard'
import { DetailTabs } from './DetailTabs'
import { HogangnonoCard } from './HogangnonoCard'
import { KbStatsCard } from './KbStatsCard'
import { LandValuationCard } from './LandValuationCard'
import { ListingComparisonCard } from './ListingComparisonCard'
import { MolitTransactionCard } from './MolitTransactionCard'
import { OpinionSection } from './OpinionSection'
import { RegionalTrendCard } from './RegionalTrendCard'
import { RiskCard } from './RiskCard'
import { Sidebar } from './Sidebar'
import { SkeletonCard } from './SkeletonCard'
import { SummaryHero } from './SummaryHero'
import { useOpinion } from '../hooks/useOpinion'

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

  const [recentItems, setRecentItems] = useState<DashboardItem[]>([])

  const [registryResult, setRegistryResult] = useState<RegistryAnalysisResult | null>(null)
  const [registryLoading, setRegistryLoading] = useState(false)
  const [registryError, setRegistryError] = useState<string | null>(null)

  const opinion = useOpinion(analysis?.property.id ?? null)

  function refreshRecent() {
    getDashboard()
      .then(setRecentItems)
      .catch(() => setRecentItems([]))
  }

  useEffect(() => {
    refreshRecent()
  }, [])

  function handleSelectSuggestion(s: AutocompleteSuggestion) {
    setQuery(s.road_address_name || s.address_name)
    setComplexHint(s.place_name || null)
  }

  async function loadMarketAndAnalysis(propertyId: number, marketQuery: string) {
    setHogangnonoLoading(true)
    getHogangnonoPrice(marketQuery, complexHint)
      .then(setHogangnonoResult)
      .catch(() => setHogangnonoResult(null))
      .finally(() => setHogangnonoLoading(false))

    const [searchResult, analysisResult] = await Promise.all([
      searchMarketTransactions(marketQuery, 3).catch(() => null),
      getPropertyAnalysis(propertyId),
    ])
    setMolitResult(searchResult)
    setAnalysis(analysisResult)
    setRegistryResult(null)
    refreshRecent()
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

    try {
      const searchResult = await searchMarketTransactions(query.trim(), 3)
      const loc = searchResult.location
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
      setMolitResult(searchResult)
      setHogangnonoLoading(true)
      getHogangnonoPrice(query.trim(), complexHint)
        .then(setHogangnonoResult)
        .catch(() => setHogangnonoResult(null))
        .finally(() => setHogangnonoLoading(false))

      const analysisResult = await getPropertyAnalysis(property.id)
      setAnalysis(analysisResult)
      setRegistryResult(null)
      refreshRecent()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '분석 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSelectRecent(propertyId: number) {
    const item = recentItems.find((i) => i.property_id === propertyId)
    if (!item) return
    setLoading(true)
    setError(null)
    setAnalysis(null)
    setMolitResult(null)
    setHogangnonoResult(null)
    try {
      await loadMarketAndAnalysis(propertyId, item.address)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '물건 정보를 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  async function handleRegistryUpload(file: File) {
    if (!analysis) return
    setRegistryLoading(true)
    setRegistryError(null)
    try {
      const result = await analyzeRegistry(file, analysis.property.id)
      setRegistryResult(result)
    } catch (err) {
      setRegistryError(err instanceof ApiError ? err.message : '등기부등본 분석 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setRegistryLoading(false)
    }
  }

  const isComparableType = analysis ? COMPARABLE_SALE_TYPES.has(analysis.property.property_type) : true

  return (
    <div className="workspace">
      <Sidebar
        query={query}
        onQueryChange={setQuery}
        onSelectSuggestion={handleSelectSuggestion}
        assetType={assetType}
        onAssetTypeChange={setAssetType}
        exclusiveArea={exclusiveArea}
        onExclusiveAreaChange={setExclusiveArea}
        floor={floor}
        onFloorChange={setFloor}
        buildYear={buildYear}
        onBuildYearChange={setBuildYear}
        onSubmit={handleSubmit}
        loading={loading}
        recentItems={recentItems}
        activePropertyId={analysis?.property.id ?? null}
        onSelectRecent={handleSelectRecent}
      />

      <main className="workspace-main">
        {error && <div className="error-banner">⚠ {error}</div>}

        {loading && (
          <>
            <SkeletonCard hero lines={2} />
            <SkeletonCard lines={4} />
          </>
        )}

        {!loading && !analysis && !error && (
          <div className="workspace-empty">
            <p className="workspace-empty-title">물건을 검색해주세요</p>
            <p>좌측에서 주소 또는 단지명을 입력하면 시세·리스크 종합분석을 시작합니다.</p>
          </div>
        )}

        {!loading && analysis && (
          <>
            <SummaryHero
              valuation={analysis.valuation}
              costIncome={analysis.cost_income_estimate}
              molit={molitResult}
              regionalTrend={analysis.regional_trend}
              hogangnono={hogangnonoResult}
              risk={analysis.risk}
              transactions={molitResult?.sale.transactions ?? []}
            />

            <DetailTabs
              tabs={[
                {
                  id: 'valuation',
                  label: '시세근거',
                  content: (
                    <>
                      {isComparableType ? (
                        molitResult && <MolitTransactionCard result={molitResult} />
                      ) : (
                        analysis.cost_income_estimate && <CostIncomeCard estimate={analysis.cost_income_estimate} />
                      )}
                      {(hogangnonoLoading || hogangnonoResult) && (
                        <HogangnonoCard result={hogangnonoResult} loading={hogangnonoLoading} />
                      )}
                      {analysis.listing_comparison && <ListingComparisonCard comparison={analysis.listing_comparison} />}
                      {analysis.land_valuation && <LandValuationCard valuation={analysis.land_valuation} />}
                      {analysis.regional_trend && <RegionalTrendCard trend={analysis.regional_trend} />}
                      <KbStatsCard sido={analysis.property.sido} />
                    </>
                  ),
                },
                {
                  id: 'risk',
                  label: '리스크상세',
                  content: <RiskCard risk={analysis.risk} />,
                },
                {
                  id: 'registry',
                  label: '권리분석',
                  content: (
                    <section className="card">
                      <h2>등기부등본 업로드</h2>
                      <p className="hint">PDF 또는 PNG/JPG 파일을 업로드하면 이 물건에 연결해 권리관계를 분석합니다.</p>
                      <input
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg"
                        disabled={registryLoading}
                        onChange={(e) => {
                          const file = e.target.files?.[0]
                          if (file) handleRegistryUpload(file)
                        }}
                      />
                      {registryLoading && <p className="hint" style={{ marginTop: 10 }}>분석 중입니다...</p>}
                      {registryError && (
                        <div className="error-banner" style={{ marginTop: 10 }}>
                          ⚠ {registryError}
                        </div>
                      )}
                      {registryResult && (
                        <div style={{ marginTop: 16 }}>
                          <p className="registry-summary">{registryResult.summary}</p>
                          <ul className="risk-flag-list">
                            {registryResult.risk_flags.map((flag) => (
                              <li key={flag}>{flag}</li>
                            ))}
                          </ul>
                          {registryResult.rights.length > 0 && (
                            <div className="table-scroll">
                              <table>
                                <thead>
                                  <tr>
                                    <th>구분</th>
                                    <th>권리유형</th>
                                    <th>권리자</th>
                                    <th>금액</th>
                                    <th>등기일</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {registryResult.rights.map((r, i) => (
                                    <tr key={i}>
                                      <td>{r.section}</td>
                                      <td>{r.right_type}</td>
                                      <td>{r.holder ?? '-'}</td>
                                      <td>{r.amount != null ? `${r.amount.toLocaleString('ko-KR')}만원` : '-'}</td>
                                      <td>{r.registered_date ?? '-'}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                          <p className="disclaimer" style={{ marginTop: 12 }}>
                            ⚠ {registryResult.disclaimer}
                          </p>
                        </div>
                      )}
                    </section>
                  ),
                },
                {
                  id: 'appraisal',
                  label: '유사사례',
                  content: <AppraisalCard appraisal={analysis.appraisal} />,
                },
              ]}
            />

            {opinion.error && <div className="error-banner">⚠ {opinion.error}</div>}
            <OpinionSection
              opinion={opinion.opinion}
              loading={opinion.loading}
              onGenerate={opinion.generate}
              onSave={opinion.save}
            />
          </>
        )}
      </main>
    </div>
  )
}
