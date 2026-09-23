import { useEffect, useRef, useState } from 'react'
import {
  analyzeRegistry,
  ApiError,
  createProperty,
  generateOpinion,
  getDashboard,
  getOpinion,
  getPropertyAnalysis,
  getRegionalStatsSummary,
  listMarketTransactions,
  listProperties,
  scrapeListings,
  searchMarketTransactions,
  updateOpinion,
} from './api/client'
import { AppraisalCard } from './components/AppraisalCard'
import { CollateralSearchView } from './components/CollateralSearchView'
import { Dashboard } from './components/Dashboard'
import { ListingComparisonCard } from './components/ListingComparisonCard'
import { ListingsCard } from './components/ListingsCard'
import { OnbidMonitorView } from './components/OnbidMonitorView'
import { OpinionSection } from './components/OpinionSection'
import { PriceTrendChart } from './components/PriceTrendChart'
import { RegionalStatsSummaryCard } from './components/RegionalStatsSummaryCard'
import { RegionalStatsView } from './components/RegionalStatsView'
import { RegistryTab } from './components/RegistryTab'
import { RiskCard } from './components/RiskCard'
import { ScoringModelView } from './components/ScoringModelView'
import { TransactionSearch } from './components/TransactionSearch'
import { ValuationCard } from './components/ValuationCard'
import type {
  AnalyzeTarget,
  DashboardItem,
  MarketSearchResult,
  MarketTransaction,
  PropertyAnalysis,
  PropertyResponse,
  RegionalBidStatSummary,
  RegistryAnalysisResult,
  ReviewOpinionResult,
} from './types'

type View = 'analysis' | 'registry' | 'dashboard' | 'regional-stats' | 'collateral-search' | 'onbid-monitor' | 'scoring-model'

function App() {
  const [view, setView] = useState<View>('analysis')
  const analysisSectionRef = useRef<HTMLDivElement>(null)

  const [analysis, setAnalysis] = useState<PropertyAnalysis | null>(null)
  const [transactions, setTransactions] = useState<MarketTransaction[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [opinion, setOpinion] = useState<ReviewOpinionResult | null>(null)
  const [opinionLoading, setOpinionLoading] = useState(false)
  const [opinionError, setOpinionError] = useState<string | null>(null)

  const [dashboardItems, setDashboardItems] = useState<DashboardItem[]>([])
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const [dashboardError, setDashboardError] = useState<string | null>(null)

  const [searchResult, setSearchResult] = useState<MarketSearchResult | null>(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  const [listingScraping, setListingScraping] = useState(false)
  const [listingScrapeError, setListingScrapeError] = useState<string | null>(null)

  const [registryProperties, setRegistryProperties] = useState<PropertyResponse[]>([])
  const [registrySelectedPropertyId, setRegistrySelectedPropertyId] = useState<number | null>(null)
  const [registryResult, setRegistryResult] = useState<RegistryAnalysisResult | null>(null)
  const [registryLoading, setRegistryLoading] = useState(false)
  const [registryError, setRegistryError] = useState<string | null>(null)

  const [regionalStatsSummary, setRegionalStatsSummary] = useState<RegionalBidStatSummary | null>(null)

  useEffect(() => {
    if (view !== 'dashboard') return
    setDashboardLoading(true)
    setDashboardError(null)
    getDashboard()
      .then(setDashboardItems)
      .catch((e) => setDashboardError(e instanceof ApiError ? e.message : '대시보드를 불러오지 못했습니다.'))
      .finally(() => setDashboardLoading(false))
  }, [view])

  useEffect(() => {
    if (view !== 'registry') return
    listProperties()
      .then(setRegistryProperties)
      .catch(() => setRegistryProperties([]))
  }, [view])

  async function loadAnalysis(propertyId: number) {
    const analysisResult = await getPropertyAnalysis(propertyId)
    const [transactionList, opinionResult] = await Promise.all([
      listMarketTransactions({
        sido: analysisResult.property.sido,
        sigungu: analysisResult.property.sigungu,
        limit: 5000,
      }),
      getOpinion(propertyId),
    ])
    setAnalysis(analysisResult)
    setTransactions(transactionList)
    setOpinion(opinionResult)

    // 지역별 입찰통계는 종합분석의 핵심 지표가 아니므로 실패해도 나머지 화면에 영향 없이 조용히 무시한다.
    getRegionalStatsSummary(analysisResult.property.sido)
      .then(setRegionalStatsSummary)
      .catch(() => setRegionalStatsSummary(null))
  }

  async function handleSearch(query: string, months: number) {
    setSearchLoading(true)
    setSearchError(null)
    try {
      const result = await searchMarketTransactions(query, months)
      setSearchResult(result)
      setAnalysis(null)
      setOpinion(null)
    } catch (e) {
      setSearchResult(null)
      setSearchError(e instanceof ApiError ? e.message : '실거래가 검색 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setSearchLoading(false)
    }
  }

  async function handleAnalyze(target: AnalyzeTarget) {
    if (!searchResult) return
    const loc = searchResult.location

    setLoading(true)
    setError(null)
    setOpinionError(null)
    try {
      const property = await createProperty({
        address: [loc.sido, loc.sigungu, loc.dong, target.complex_name].filter(Boolean).join(' '),
        sido: loc.sido,
        sigungu: loc.sigungu,
        dong: loc.dong,
        property_type: '아파트',
        complex_name: target.complex_name,
        exclusive_area: target.exclusive_area,
        floor: target.floor,
        total_floors: null,
        build_year: target.build_year,
        household_count: null,
      })
      await loadAnalysis(property.id)
      // 결과 DOM이 렌더링된 다음 프레임에 스크롤해야 정확한 위치로 이동한다.
      requestAnimationFrame(() => {
        analysisSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    } catch (e) {
      setAnalysis(null)
      setError(e instanceof ApiError ? e.message : '분석 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSelectProperty(propertyId: number) {
    setView('analysis')
    setSearchResult(null)
    setLoading(true)
    setError(null)
    try {
      await loadAnalysis(propertyId)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : '물건 정보를 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }

  async function handleRegistryUpload(file: File) {
    setRegistryLoading(true)
    setRegistryError(null)
    try {
      const result = await analyzeRegistry(file, registrySelectedPropertyId ?? undefined)
      setRegistryResult(result)
    } catch (e) {
      setRegistryError(e instanceof ApiError ? e.message : '등기부등본 분석 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setRegistryLoading(false)
    }
  }

  async function handleScrapeListings() {
    if (!analysis?.property.complex_name) return
    setListingScraping(true)
    setListingScrapeError(null)
    try {
      await scrapeListings({
        complex_name: analysis.property.complex_name,
        sigungu: analysis.property.sigungu,
        reference_area: analysis.appraisal.reference_area,
        reference_unit_price: analysis.appraisal.reference_price_per_area,
      })
      await loadAnalysis(analysis.property.id) // 최신 매물·괴리율을 반영해 전체 재조회
    } catch (e) {
      setListingScrapeError(e instanceof ApiError ? e.message : '매물 수집 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setListingScraping(false)
    }
  }

  async function handleGenerateOpinion() {
    if (!analysis) return
    setOpinionLoading(true)
    setOpinionError(null)
    try {
      const result = await generateOpinion(analysis.property.id)
      setOpinion(result)
    } catch (e) {
      setOpinionError(e instanceof ApiError ? e.message : '심사의견 생성 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setOpinionLoading(false)
    }
  }

  async function handleSaveOpinion(content: string) {
    if (!analysis) return
    setOpinionLoading(true)
    setOpinionError(null)
    try {
      const result = await updateOpinion(analysis.property.id, content)
      setOpinion(result)
    } catch (e) {
      setOpinionError(e instanceof ApiError ? e.message : '심사의견 저장 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setOpinionLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-row">
          <div>
            <h1>부동산 시세·리스크 종합분석</h1>
            <p className="app-subtitle">담보가치·리스크 판단을 돕는 AI 참고 도구입니다. 최종 심사 판단은 심사역이 수행합니다.</p>
          </div>
          <nav className="tab-nav">
            <button type="button" className={view === 'analysis' ? 'tab-active' : ''} onClick={() => setView('analysis')}>
              종합분석
            </button>
            <button type="button" className={view === 'registry' ? 'tab-active' : ''} onClick={() => setView('registry')}>
              권리분석
            </button>
            <button type="button" className={view === 'dashboard' ? 'tab-active' : ''} onClick={() => setView('dashboard')}>
              대시보드
            </button>
            <button
              type="button"
              className={view === 'regional-stats' ? 'tab-active' : ''}
              onClick={() => setView('regional-stats')}
            >
              지역별 입찰통계
            </button>
            <button
              type="button"
              className={view === 'collateral-search' ? 'tab-active' : ''}
              onClick={() => setView('collateral-search')}
            >
              담보물건 검색
            </button>
            <button
              type="button"
              className={view === 'onbid-monitor' ? 'tab-active' : ''}
              onClick={() => setView('onbid-monitor')}
            >
              경매·공매 모니터링
            </button>
            <button
              type="button"
              className={view === 'scoring-model' ? 'tab-active' : ''}
              onClick={() => setView('scoring-model')}
            >
              스코어링 모델
            </button>
          </nav>
        </div>
      </header>

      {view === 'dashboard' ? (
        <main className="dashboard-layout">
          <Dashboard items={dashboardItems} loading={dashboardLoading} error={dashboardError} onSelect={handleSelectProperty} />
        </main>
      ) : view === 'regional-stats' ? (
        <main className="dashboard-layout">
          <RegionalStatsView />
        </main>
      ) : view === 'collateral-search' ? (
        <main className="dashboard-layout">
          <CollateralSearchView />
        </main>
      ) : view === 'onbid-monitor' ? (
        <main className="dashboard-layout">
          <OnbidMonitorView />
        </main>
      ) : view === 'scoring-model' ? (
        <main className="dashboard-layout">
          <ScoringModelView />
        </main>
      ) : view === 'registry' ? (
        <main className="dashboard-layout">
          <RegistryTab
            properties={registryProperties}
            selectedPropertyId={registrySelectedPropertyId}
            onSelectProperty={setRegistrySelectedPropertyId}
            onUpload={handleRegistryUpload}
            loading={registryLoading}
            error={registryError}
            result={registryResult}
          />
        </main>
      ) : (
        <main className="dashboard-layout">
          <TransactionSearch
            onSearch={handleSearch}
            onAnalyze={handleAnalyze}
            result={searchResult}
            loading={searchLoading}
            analyzing={loading}
            error={searchError}
          />

          {error && <div className="error-banner">⚠ {error}</div>}
          {loading && <div className="placeholder">분석 중입니다...</div>}

          {analysis && (
            <div className="search-view" ref={analysisSectionRef}>
              <div className="ai-draft-banner">
                🤖 3. AI 추정시세·담보리스크·유사사례 — 심사역 검토 전 참고용 분석 결과입니다.
              </div>

              <div className="results-grid">
                <ValuationCard valuation={analysis.valuation} />
                <RiskCard risk={analysis.risk} />
              </div>

              {regionalStatsSummary && <RegionalStatsSummaryCard summary={regionalStatsSummary} />}

              <AppraisalCard appraisal={analysis.appraisal} />
              {analysis.listings && (
                <ListingsCard
                  listings={analysis.listings}
                  onScrape={handleScrapeListings}
                  scraping={listingScraping}
                  scrapeError={listingScrapeError}
                />
              )}
              {analysis.listing_comparison && <ListingComparisonCard comparison={analysis.listing_comparison} />}

              {opinionError && <div className="error-banner">⚠ {opinionError}</div>}
              <OpinionSection
                opinion={opinion}
                loading={opinionLoading}
                onGenerate={handleGenerateOpinion}
                onSave={handleSaveOpinion}
              />

              <PriceTrendChart transactions={transactions} />
            </div>
          )}
        </main>
      )}
    </div>
  )
}

export default App
