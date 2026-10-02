import type {
  AutocompleteSuggestion,
  CollateralScoreModelInfo,
  CollateralScoreTrainResult,
  CollectionRunResult,
  CourtAuctionDailyCollectionSummary,
  CourtAuctionDailyItemsResponse,
  DailyCollectionSummary,
  DailyItemsResponse,
  DashboardItem,
  HogangnonoComplexResult,
  KbPriceTrendResponse,
  ListingScrapeResponse,
  MarketSearchResult,
  MarketTransaction,
  PropertyAnalysis,
  PropertyCreate,
  PropertyResponse,
  RegionalBidStatSummary,
  RegionalBidStatTrend,
  RegistryAnalysisResult,
  ReviewOpinionResult,
} from '../types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function throwIfError(res: Response): Promise<void> {
  if (res.ok) return
  const body = await res.json().catch(() => null)
  const detail = body?.detail ? (typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)) : res.statusText
  throw new ApiError(detail, res.status)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  await throwIfError(res)
  return res.json() as Promise<T>
}

export function createProperty(payload: PropertyCreate): Promise<PropertyResponse> {
  return request<PropertyResponse>('/properties', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getPropertyAnalysis(propertyId: number): Promise<PropertyAnalysis> {
  return request<PropertyAnalysis>(`/properties/${propertyId}/analysis`)
}

export function listProperties(): Promise<PropertyResponse[]> {
  return request<PropertyResponse[]>('/properties')
}

export function listMarketTransactions(params: {
  sido: string
  sigungu: string
  limit?: number
}): Promise<MarketTransaction[]> {
  const search = new URLSearchParams({
    sido: params.sido,
    sigungu: params.sigungu,
    limit: String(params.limit ?? 300),
  })
  return request<MarketTransaction[]>(`/market-data/transactions?${search.toString()}`)
}

export async function analyzeRegistry(file: File, propertyId?: number): Promise<RegistryAnalysisResult> {
  const formData = new FormData()
  formData.append('file', file)
  if (propertyId != null) formData.append('property_id', String(propertyId))

  // multipart 요청은 브라우저가 boundary를 포함한 Content-Type을 직접 설정해야 하므로
  // request()의 기본 JSON 헤더를 쓰지 않고 fetch를 직접 호출한다.
  const res = await fetch(`${BASE_URL}/registry/analyze`, {
    method: 'POST',
    body: formData,
  })
  await throwIfError(res)
  return res.json() as Promise<RegistryAnalysisResult>
}

export function generateOpinion(propertyId: number): Promise<ReviewOpinionResult> {
  return request<ReviewOpinionResult>(`/properties/${propertyId}/opinion/generate`, { method: 'POST' })
}

export async function getOpinion(propertyId: number): Promise<ReviewOpinionResult | null> {
  try {
    return await request<ReviewOpinionResult>(`/properties/${propertyId}/opinion`)
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
}

export function updateOpinion(propertyId: number, content: string): Promise<ReviewOpinionResult> {
  return request<ReviewOpinionResult>(`/properties/${propertyId}/opinion`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  })
}

export function getDashboard(): Promise<DashboardItem[]> {
  return request<DashboardItem[]>('/dashboard')
}

export function searchMarketTransactions(query: string, months: number): Promise<MarketSearchResult> {
  const search = new URLSearchParams({ query, months: String(months) })
  return request<MarketSearchResult>(`/market-data/search?${search.toString()}`)
}

export function scrapeListings(params: {
  complex_name: string
  sigungu?: string | null
  reference_area?: number | null
  reference_unit_price?: number | null
}): Promise<ListingScrapeResponse> {
  return request<ListingScrapeResponse>('/listings/scrape', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export function listRegionalStatsRegions(): Promise<string[]> {
  return request<string[]>('/onbid-stats/regions')
}

export function getRegionalStatsTrend(sido: string, sigungu?: string | null): Promise<RegionalBidStatTrend> {
  const search = new URLSearchParams({ sido })
  if (sigungu) search.set('sigungu', sigungu)
  return request<RegionalBidStatTrend>(`/onbid-stats/trend?${search.toString()}`)
}

export function getRegionalStatsSummary(sido: string, sigungu?: string | null): Promise<RegionalBidStatSummary> {
  const search = new URLSearchParams({ sido })
  if (sigungu) search.set('sigungu', sigungu)
  return request<RegionalBidStatSummary>(`/onbid-stats/summary?${search.toString()}`)
}

export function autocompleteSearch(query: string): Promise<AutocompleteSuggestion[]> {
  const search = new URLSearchParams({ query })
  return request<AutocompleteSuggestion[]>(`/search/autocomplete?${search.toString()}`)
}

export function getHogangnonoPrice(query: string, complexName?: string | null): Promise<HogangnonoComplexResult> {
  const search = new URLSearchParams({ query })
  if (complexName) search.set('complex_name', complexName)
  return request<HogangnonoComplexResult>(`/hogangnono/price?${search.toString()}`)
}

export function listOnbidCollectionDates(days = 30): Promise<DailyCollectionSummary[]> {
  const search = new URLSearchParams({ days: String(days) })
  return request<DailyCollectionSummary[]>(`/onbid-monitor/collection-dates?${search.toString()}`)
}

export function getOnbidDailyItems(targetDate?: string): Promise<DailyItemsResponse> {
  const search = targetDate ? `?${new URLSearchParams({ target_date: targetDate }).toString()}` : ''
  return request<DailyItemsResponse>(`/onbid-monitor/daily-items${search}`)
}

export function getCollateralScoreModelInfo(): Promise<CollateralScoreModelInfo> {
  return request<CollateralScoreModelInfo>('/collateral-score/model-info')
}

export function trainCollateralScoreModel(): Promise<CollateralScoreTrainResult> {
  return request<CollateralScoreTrainResult>('/collateral-score/train', { method: 'POST' })
}

export function listCourtAuctionCollectionDates(days = 30): Promise<CourtAuctionDailyCollectionSummary[]> {
  const search = new URLSearchParams({ days: String(days) })
  return request<CourtAuctionDailyCollectionSummary[]>(`/court-auction-monitor/collection-dates?${search.toString()}`)
}

export function getCourtAuctionDailyItems(targetDate?: string): Promise<CourtAuctionDailyItemsResponse> {
  const search = targetDate ? `?${new URLSearchParams({ target_date: targetDate }).toString()}` : ''
  return request<CourtAuctionDailyItemsResponse>(`/court-auction-monitor/daily-items${search}`)
}

export function collectCourtAuctionNow(): Promise<CollectionRunResult> {
  return request<CollectionRunResult>('/court-auction-monitor/collect', { method: 'POST' })
}

export function getKbPriceTrend(sido: string, months = 24): Promise<KbPriceTrendResponse> {
  const search = new URLSearchParams({ sido, months: String(months) })
  return request<KbPriceTrendResponse>(`/kb-stats/trend?${search.toString()}`)
}

export { ApiError }
