import { useTheme } from '../ThemeContext'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button type="button" className="theme-toggle" onClick={toggleTheme} aria-label={isDark ? '라이트 모드로 전환' : '다크 모드로 전환'}>
      {isDark ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.742 13.045a8.088 8.088 0 0 1-2.077.273c-4.624 0-8.371-3.747-8.371-8.371 0-1.191.248-2.323.696-3.346a.75.75 0 0 0-.933-.998A10.095 10.095 0 1 0 22.08 13.902a.75.75 0 0 0-1.338-.857Z" />
        </svg>
      )}
      <span>{isDark ? '라이트' : '다크'}</span>
    </button>
  )
}
