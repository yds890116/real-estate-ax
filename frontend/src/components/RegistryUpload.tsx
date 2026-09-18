import { useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import type { PropertyResponse } from '../types'

interface Props {
  onUpload: (file: File) => void
  loading: boolean
  properties: PropertyResponse[]
  selectedPropertyId: number | null
  onSelectProperty: (id: number | null) => void
}

export function RegistryUpload({ onUpload, loading, properties, selectedPropertyId, onSelectProperty }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [fileName, setFileName] = useState<string | null>(null)

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    onUpload(file)
  }

  return (
    <section className="card registry-upload">
      <h2>1. 등기부등본 업로드</h2>
      <p className="hint">
        PDF(텍스트 추출) 또는 PNG/JPG 파일을 업로드하면 갑구·을구 권리사항(근저당권·가압류 등)을 자동으로 분석합니다.
      </p>

      <label className="opinion-label" htmlFor="registry-property-select">
        연결할 물건 (선택)
      </label>
      <select
        id="registry-property-select"
        value={selectedPropertyId ?? ''}
        onChange={(e) => onSelectProperty(e.target.value ? Number(e.target.value) : null)}
        disabled={loading}
      >
        <option value="">연결 안 함 (독립 분석)</option>
        {properties.map((p) => (
          <option key={p.id} value={p.id}>
            {p.address}
          </option>
        ))}
      </select>
      <p className="hint">물건을 연결하면 AI 추정시세와 비교한 근저당권 비율까지 함께 분석합니다.</p>

      <input ref={inputRef} type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={handleChange} disabled={loading} />
      {loading && <p className="hint">분석 중입니다...</p>}
      {fileName && !loading && <p className="hint">최근 업로드: {fileName}</p>}
    </section>
  )
}
