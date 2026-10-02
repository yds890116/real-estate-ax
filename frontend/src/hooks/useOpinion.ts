import { useEffect, useState } from 'react'
import { ApiError, generateOpinion, getOpinion, updateOpinion } from '../api/client'
import type { ReviewOpinionResult } from '../types'

/** propertyId가 바뀔 때마다 기존 심사의견을 불러오고, 생성/저장 액션을 제공한다. */
export function useOpinion(propertyId: number | null) {
  const [opinion, setOpinion] = useState<ReviewOpinionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (propertyId == null) {
      setOpinion(null)
      return
    }
    getOpinion(propertyId)
      .then(setOpinion)
      .catch(() => setOpinion(null))
  }, [propertyId])

  async function generate() {
    if (propertyId == null) return
    setLoading(true)
    setError(null)
    try {
      setOpinion(await generateOpinion(propertyId))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : '심사의견 생성 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  async function save(content: string) {
    if (propertyId == null) return
    setLoading(true)
    setError(null)
    try {
      setOpinion(await updateOpinion(propertyId, content))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : '심사의견 저장 중 알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return { opinion, loading, error, generate, save }
}
