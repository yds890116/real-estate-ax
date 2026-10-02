import { useEffect, useState } from 'react'
import type { ReviewOpinionResult } from '../types'

interface Props {
  opinion: ReviewOpinionResult | null
  loading: boolean
  onGenerate: () => void
  onSave: (content: string) => void
}

export function OpinionSection({ opinion, loading, onGenerate, onSave }: Props) {
  const [draft, setDraft] = useState(opinion?.current_content ?? '')
  const [showAiDraft, setShowAiDraft] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    setDraft(opinion?.current_content ?? '')
  }, [opinion?.id, opinion?.current_content])

  const isEdited = opinion ? opinion.current_content !== opinion.ai_draft : false
  const hasUnsavedChanges = opinion ? draft !== opinion.current_content : false

  return (
    <section className="card">
      <div className="card-header">
        <h2>심사의견 초안</h2>
        {opinion && (
          <span className={`badge ${opinion.generation_method === 'llm' ? 'badge-ml' : 'badge-rule'}`}>
            {opinion.generation_method === 'llm' ? 'Claude 생성' : '템플릿 생성'}
          </span>
        )}
      </div>

      {!opinion ? (
        <>
          <p className="hint">시세·리스크·권리관계·유사사례 분석 결과를 종합해 심사의견 초안을 자동 생성합니다.</p>
          <button type="button" onClick={onGenerate} disabled={loading}>
            {loading ? '생성 중...' : '심사의견 초안 생성'}
          </button>
        </>
      ) : (
        <>
          {isEdited && <p className="hint">심사역이 초안을 수정한 최종본입니다.</p>}

          <button type="button" className="link-button" onClick={() => setShowAiDraft((v) => !v)}>
            {showAiDraft ? '원본 숨기기 ▲' : '생성 원본 보기 ▼'}
          </button>
          {showAiDraft && (
            <div className="opinion-ai-block">
              <pre className="opinion-readonly">{opinion.ai_draft}</pre>
            </div>
          )}

          <label className="opinion-label" htmlFor="opinion-final">
            심사역 최종본 (수정 가능)
          </label>
          <textarea
            id="opinion-final"
            className="opinion-textarea"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={14}
          />

          <div className="opinion-actions">
            <button type="button" onClick={() => onSave(draft)} disabled={!hasUnsavedChanges || loading}>
              저장
            </button>
            <button type="button" className="secondary-button" onClick={onGenerate} disabled={loading}>
              {loading ? '재생성 중...' : 'AI 초안 재생성'}
            </button>
          </div>

          {opinion.edit_history.length > 0 && (
            <>
              <button type="button" className="link-button" onClick={() => setShowHistory((v) => !v)}>
                수정 이력 {opinion.edit_history.length}건 {showHistory ? '숨기기 ▲' : '보기 ▼'}
              </button>
              {showHistory && (
                <ul className="opinion-history">
                  {[...opinion.edit_history].reverse().map((h) => (
                    <li key={h.saved_at}>
                      <span className="hint">{new Date(h.saved_at).toLocaleString('ko-KR')}</span>
                      <pre className="opinion-readonly">{h.content}</pre>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}

          <p className="disclaimer">⚠ {opinion.disclaimer}</p>
        </>
      )}
    </section>
  )
}
