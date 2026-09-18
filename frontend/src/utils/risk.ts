export function gradeColorClass(grade: number): string {
  if (grade <= 2) return 'grade-safe'
  if (grade <= 4) return 'grade-good'
  if (grade <= 6) return 'grade-caution'
  if (grade <= 8) return 'grade-warning'
  return 'grade-danger'
}

export function tierColorClass(tier: '상' | '중' | '하'): string {
  if (tier === '하') return 'grade-safe'
  if (tier === '중') return 'grade-caution'
  return 'grade-danger'
}
