// 백엔드 금액 단위는 모두 "만원"
export function formatManwon(amount: number): string {
  const eok = Math.floor(amount / 10000)
  const remain = Math.round(amount - eok * 10000)

  if (eok > 0 && remain > 0) return `${eok}억 ${remain.toLocaleString('ko-KR')}만원`
  if (eok > 0) return `${eok}억원`
  return `${remain.toLocaleString('ko-KR')}만원`
}

export function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`
}

export function formatDate(dateStr: string): string {
  return dateStr.slice(0, 10)
}
