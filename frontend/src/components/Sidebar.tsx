import type { FormEvent } from 'react'
import type { AutocompleteSuggestion, DashboardItem } from '../types'
import { formatManwon } from '../utils/format'
import { gradeColorClass } from '../utils/risk'
import { AutocompleteSearchBox } from './AutocompleteSearchBox'

const ASSET_TYPES = ['아파트', '빌라', '오피스텔', '상가', '단독주택', '기타']

interface Props {
  query: string
  onQueryChange: (value: string) => void
  onSelectSuggestion: (suggestion: AutocompleteSuggestion) => void
  assetType: string
  onAssetTypeChange: (value: string) => void
  exclusiveArea: string
  onExclusiveAreaChange: (value: string) => void
  floor: string
  onFloorChange: (value: string) => void
  buildYear: string
  onBuildYearChange: (value: string) => void
  onSubmit: (e: FormEvent) => void
  loading: boolean
  recentItems: DashboardItem[]
  activePropertyId: number | null
  onSelectRecent: (propertyId: number) => void
}

export function Sidebar({
  query,
  onQueryChange,
  onSelectSuggestion,
  assetType,
  onAssetTypeChange,
  exclusiveArea,
  onExclusiveAreaChange,
  floor,
  onFloorChange,
  buildYear,
  onBuildYearChange,
  onSubmit,
  loading,
  recentItems,
  activePropertyId,
  onSelectRecent,
}: Props) {
  return (
    <aside className="workspace-sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-name">담보가치 AI</span>
        <span className="sidebar-brand-tag">시세·리스크 참고 도구</span>
      </div>

      <form className="sidebar-search-form" onSubmit={onSubmit}>
        <p className="sidebar-section-title">물건 검색</p>
        <AutocompleteSearchBox
          value={query}
          onChange={onQueryChange}
          onSelect={onSelectSuggestion}
          placeholder="주소 또는 단지명 검색"
        />
        <div className="sidebar-form-grid">
          <label>
            자산유형
            <select value={assetType} onChange={(e) => onAssetTypeChange(e.target.value)}>
              {ASSET_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label>
            전용면적(㎡)
            <input
              type="number"
              step="0.01"
              value={exclusiveArea}
              onChange={(e) => onExclusiveAreaChange(e.target.value)}
              required
            />
          </label>
          <label>
            층
            <input type="number" value={floor} onChange={(e) => onFloorChange(e.target.value)} placeholder="선택" />
          </label>
          <label>
            준공연도
            <input type="number" value={buildYear} onChange={(e) => onBuildYearChange(e.target.value)} placeholder="선택" />
          </label>
        </div>
        <button type="submit" className="sidebar-submit" disabled={loading}>
          {loading ? '분석 중...' : '종합분석 조회'}
        </button>
      </form>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1, minHeight: 0 }}>
        <p className="sidebar-section-title">최근 조회</p>
        <div className="recent-list">
          {recentItems.length === 0 && <p className="recent-empty">최근 조회한 물건이 없습니다.</p>}
          {recentItems.map((item) => (
            <button
              key={item.property_id}
              type="button"
              className={`recent-item ${item.property_id === activePropertyId ? 'recent-item-active' : ''}`}
              onClick={() => onSelectRecent(item.property_id)}
            >
              <span className="recent-item-address">{item.address}</span>
              <span className="recent-item-meta">
                <span className={`risk-grade-badge-sm ${gradeColorClass(item.risk_grade)}`} style={{ width: 16, height: 16, fontSize: 9 }}>
                  {item.risk_grade}
                </span>
                <span className="recent-item-price">{formatManwon(item.estimated_price)}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </aside>
  )
}
