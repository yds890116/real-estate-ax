import { RegistryCard } from './RegistryCard'
import { RegistryCharts } from './RegistryCharts'
import { RegistryUpload } from './RegistryUpload'
import type { PropertyResponse, RegistryAnalysisResult } from '../types'

interface Props {
  properties: PropertyResponse[]
  selectedPropertyId: number | null
  onSelectProperty: (id: number | null) => void
  onUpload: (file: File) => void
  loading: boolean
  error: string | null
  result: RegistryAnalysisResult | null
}

export function RegistryTab({ properties, selectedPropertyId, onSelectProperty, onUpload, loading, error, result }: Props) {
  return (
    <div className="search-view">
      <RegistryUpload
        onUpload={onUpload}
        loading={loading}
        properties={properties}
        selectedPropertyId={selectedPropertyId}
        onSelectProperty={onSelectProperty}
      />

      {error && <div className="error-banner">⚠ {error}</div>}
      {loading && <div className="placeholder">등기부등본을 분석하는 중입니다...</div>}

      {!result && !loading && !error && (
        <div className="placeholder">등기부등본을 업로드하면 권리분석 결과가 여기에 표시됩니다.</div>
      )}

      {result && (
        <>
          <RegistryCard registry={result} />
          <RegistryCharts rights={result.rights} mortgageTotal={result.mortgage_total} estimatedPrice={result.estimated_price} />
        </>
      )}
    </div>
  )
}
