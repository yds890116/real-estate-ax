import { useState } from 'react'
import type { ReactNode } from 'react'

interface Tab {
  id: string
  label: string
  content: ReactNode
}

export function DetailTabs({ tabs }: { tabs: Tab[] }) {
  const [activeId, setActiveId] = useState(tabs[0]?.id)
  const active = tabs.find((t) => t.id === activeId) ?? tabs[0]

  return (
    <div className="detail-tabs">
      <div className="detail-tabs-nav">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={t.id === active?.id ? 'detail-tab-active' : ''}
            onClick={() => setActiveId(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="detail-tabs-panel">{active?.content}</div>
    </div>
  )
}
