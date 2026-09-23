export function SkeletonCard({ lines = 3, hero = false }: { lines?: number; hero?: boolean }) {
  return (
    <section className="card skeleton-card" aria-busy="true" aria-label="불러오는 중">
      <div className="skeleton-block skeleton-title" />
      {hero && <div className="skeleton-block skeleton-hero" />}
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`skeleton-block skeleton-line ${i === lines - 1 ? 'short' : ''}`} />
      ))}
    </section>
  )
}
