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
  regional_trend: RegionTrendFeatures | null
  cost_income_estimate: CostIncomeEstimate | null
}

export interface RegionTrendFeatures {
  sido: string
  sigungu: string | null
  region_matched: string | null
  apt_actual_txn_sale_latest: number | null
  apt_actual_txn_sale_mom_change_pct: number | null
  apt_price_trend_sale_latest: number | null
  apt_price_trend_sale_mom_change_pct: number | null
  apt_price_trend_jeonse_latest: number | null
  apt_price_trend_jeonse_mom_change_pct: number | null
  land_price_change_latest: number | null
  land_price_change_unit: string | null
  land_price_change_period: string | null
  rental_trend_office_latest: number | null
  rental_trend_office_unit: string | null
  rental_trend_office_period: string | null
}

export interface CostIncomeEstimate {
  property_type: string
  replacement_cost_per_area: number
  depreciation_rate_pct: number
  cost_approach_price: number
  unit_rent_per_area: number
  vacancy_rate_pct: number
  opex_ratio_pct: number
  cap_rate_pct: number
  annual_noi: number
  income_approach_price: number
  estimated_price: number
  price_per_area: number
  confidence_level: number
  disclaimer: string
}

export interface HogangnonoAreaPrice {
  area_no: number
  private_area: number
  real_trade_price: number | null
  portal_trade_price: number | null
  real_rent_price: number | null
  portal_rent_price: number | null
}

export interface HogangnonoListingItem {
  item_id: number
  trade_type: '매매' | '전세' | '월세' | '기타'
  price: number
  monthly_rent: number | null
  private_area: number
  public_area: number | null
  floor_tier: string | null
  dong_name: string | null
  room_type: string | null
  title: string | null
}

export interface HogangnonoComplexResult {
  found: boolean
  complex_name: string | null
  address: string | null
  road_address: string | null
  total_household: number | null
  areas: HogangnonoAreaPrice[]
  listings: HogangnonoListingItem[]
  source: string
  notice: string | null
}

export interface AutocompleteSuggestion {
  place_name: string
  address_name: string
  road_address_name: string | null
  x: string
  y: string
  category_group_name: string | null
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

export interface CollateralScore {
  score: number
  grade: number
  grade_label: string
  method: 'ml' | 'rule'
  observed_uscbd_cnt: number
}

export interface OnbidAuctionItemResponse {
  id: number
  cltr_mnmt_no: string
  plnm_no: string | null
  pbct_no: string | null
  cltr_nm: string | null
  ctgr_full_nm: string | null
  ldnm_adrs: string | null
  nmrd_adrs: string | null
  dpsl_mtd_nm: string | null
  bid_mtd_nm: string | null
  min_bid_prc: number | null
  apsl_ases_avg_amt: number | null
  fee_rate: string | null
  pbct_begn_dtm: string | null
  pbct_cls_dtm: string | null
  pbct_cltr_stat_nm: string | null
  uscbd_cnt: number | null
  appraisal_amt: number | null
  appraisal_date: string | null
  appraisal_org_nm: string | null
  collected_at: string
  score: CollateralScore | null
}

export interface DailyCollectionSummary {
  collected_date: string
  item_count: number
}

export interface DailyItemsResponse {
  date: string
  items: OnbidAuctionItemResponse[]
}

export interface CollateralScoreTrainResult {
  n_rows: number
  trained_at: string
  source_breakdown: Record<string, number>
  feature_importances: Record<string, number>
  mae: number
  rmse: number
  r2: number
}

export interface CollateralScoreModelInfo {
  is_available: boolean
  n_rows: number
  source_breakdown: Record<string, number>
  trained_at: string | null
  metrics: Record<string, number>
  feature_importances: Record<string, number>
  feature_descriptions: Record<string, string>
  target_description: string
}

export interface CourtAuctionItemResponse {
  id: number
  docid: string
  case_no: string
  item_no: string | null
  court_name: string | null
  dept_name: string | null
  usage_name: string | null
  address: string | null
  building_detail: string | null
  remarks: string | null
  appraisal_amt: number | null
  min_sale_price: number | null
  min_sale_price_rate: string | null
  failed_count: number | null
  sale_date: string | null
  status: string | null
  collected_at: string
}

export interface CourtAuctionDailyCollectionSummary {
  collected_date: string
  item_count: number
}

export interface CourtAuctionDailyItemsResponse {
  date: string
  items: CourtAuctionItemResponse[]
}

export interface CollectionRunResult {
  collected: number
  skipped: number
  failed: number
  status: string
  error: string | null
  appraisal_enriched: number
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
