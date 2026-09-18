export interface PropertyCreate {
  address: string
  sido: string
  sigungu: string
  dong?: string | null
  property_type: string
  complex_name?: string | null
  exclusive_area: number
  floor?: number | null
  total_floors?: number | null
  build_year?: number | null
  household_count?: number | null
}

export interface PropertyResponse extends PropertyCreate {
  id: number
  created_at: string
}

export interface ValuationResult {
  estimated_price: number
  price_lower: number
  price_upper: number
  confidence_level: number
  price_per_area: number
  comparable_count: number
  model_version: string
  disclaimer: string
}

export interface RiskFactor {
  name: string
  description: string
  impact: 'positive' | 'negative' | 'neutral'
  weight: number
  method: 'rule' | 'ml'
}

export interface RiskIndicator {
  key: string
  label: string
  description: string
  normalized_score: number
  weight: number
  method: 'rule' | 'ml'
  available: boolean
}

export interface RiskCategory {
  key: string
  label: string
  weight: number
  normalized_score: number
  contribution: number
  indicators: RiskIndicator[]
}

export interface RiskScoreResult {
  risk_grade: number
  risk_level_label: string
  grade_tier: '상' | '중' | '하'
  score: number
  model_version: string
  categories: RiskCategory[]
  factors: RiskFactor[]
  disclaimer: string
}

export interface PropertyAnalysis {
  property: PropertyResponse
  valuation: ValuationResult
  risk: RiskScoreResult
  registry: RegistryAnalysisResult | null
  appraisal: AppraisalSearchResult
  listings: ListingSearchResult | null
  listing_comparison: ListingComparison | null
}

export interface ListingItem {
  id: string
  complex_name: string
  exclusive_area: number
  floor: string
  trade_type: '매매' | '전세' | '월세'
  price: number
  monthly_rent: number | null
  realtor: string | null
  source: 'naver_scrape' | 'sample'
}

export interface ListingSearchResult {
  complex_name: string
  reference_area: number
  listings: ListingItem[]
  source: 'naver_scrape' | 'sample'
  is_sample_data: boolean
  notice: string
}

export interface ListingScrapeResponse {
  complex_name: string
  source: 'naver_scrape' | 'sample'
  blocked: boolean
  block_reason: string | null
  listings: ListingItem[]
}

export interface ListingComparison {
  reference_area: number
  market_unit_price: number | null
  listing_unit_price: number | null
  gap_ratio: number | null
  listing_count: number
  market_transaction_count: number
  explanation: string
}

export interface AppraisalCaseItem {
  id: number
  source_file: string
  case_type: string
  sido: string | null
  sigungu: string | null
  dong: string
  jibun: string | null
  complex_name: string
  dong_ho: string | null
  usage: string
  exclusive_area: number
  event_date: string
  purpose: string | null
  amount: number
  unit_price: number
  location_note: string | null
  approval_date: string | null
  similarity: number | null
}

export interface AppraisalSearchResult {
  cases: AppraisalCaseItem[]
  reference_price_per_area: number | null
  reference_price: number | null
  reference_area: number | null
  explanation: string
  generation_method: 'llm' | 'template'
  disclaimer: string
}

export interface RegistryRight {
  section: string
  rank: string | null
  right_type: string
  holder: string | null
  amount: number | null
  registered_date: string | null
  raw_text: string
}

export interface RegistryAnalysisResult {
  id: number
  property_id: number | null
  filename: string
  rights: RegistryRight[]
  risk_flags: string[]
  summary: string
  generation_method: 'llm' | 'template'
  mortgage_total: number | null
  estimated_price: number | null
  disclaimer: string
}

export interface OpinionEditHistoryEntry {
  content: string
  saved_at: string
}

export interface ReviewOpinionResult {
  id: number
  property_id: number
  ai_draft: string
  current_content: string
  edit_history: OpinionEditHistoryEntry[]
  generation_method: 'llm' | 'template'
  created_at: string
  updated_at: string
  disclaimer: string
}

export interface DashboardItem {
  property_id: number
  address: string
  sido: string
  sigungu: string
  property_type: string
  exclusive_area: number
  estimated_price: number
  price_per_area: number
  risk_grade: number
  risk_level_label: string
  has_registry: boolean
  registry_risk_count: number
  reference_price: number | null
  price_gap_ratio: number | null
  opinion_status: 'none' | 'draft' | 'edited'
  alerts: string[]
  created_at: string
}

export interface LocationResolved {
  query: string
  sido: string
  sigungu: string
  dong: string | null
  lawd_cd: string
  jibun: string | null
  complex_name_hint: string | null
  source: 'address' | 'keyword'
}

export interface SaleSearchGroup {
  total_fetched: number
  total_matched: number
  transactions: MarketTransaction[]
}

export interface RentSearchGroup {
  total_fetched: number
  total_matched: number
  transactions: RentTransaction[]
}

export interface MarketSearchResult {
  location: LocationResolved
  months_searched: string[]
  filter_applied: string | null
  sale: SaleSearchGroup
  rent: RentSearchGroup
}

export interface MarketTransaction {
  id: number
  sido: string
  sigungu: string
  dong: string | null
  complex_name: string | null
  exclusive_area: number
  floor: number | null
  build_year: number | null
  deal_price: number
  deal_date: string
  source: string
}

export interface AnalyzeTarget {
  complex_name: string | null
  exclusive_area: number
  floor: number | null
  build_year: number | null
}

export interface RegionalBidStatItem {
  id: number
  sido: string
  sigungu: string | null
  period: string
  period_type: 'year' | 'month' | 'quarter'
  bid_count: number | null
  win_count: number | null
  win_rate: number | null
  avg_appraisal_amt: number | null
  avg_min_bid_amt: number | null
  avg_win_bid_amt: number | null
  avg_bid_rate_vs_appraisal: number | null
  avg_bid_rate_vs_min_bid: number | null
  bidder_count: number | null
  competition_rate: number | null
  source: string
}

export interface RegionalBidStatTrend {
  sido: string
  sigungu: string | null
  items: RegionalBidStatItem[]
  source: 'onbid_stats_api' | 'sample'
  is_sample_data: boolean
  notice: string
}

export interface RegionalBidStatSummary {
  sido: string
  sigungu: string | null
  latest: RegionalBidStatItem | null
  source: 'onbid_stats_api' | 'sample'
  is_sample_data: boolean
  notice: string
}

export interface RentTransaction {
  id: number
  sido: string
  sigungu: string
  dong: string | null
  complex_name: string | null
  exclusive_area: number
  floor: number | null
  build_year: number | null
  deposit: number
  monthly_rent: number
  contract_type: '전세' | '월세'
  deal_date: string
  source: string
}
