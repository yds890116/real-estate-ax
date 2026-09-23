import { useEffect, useRef, useState } from 'react'
import { autocompleteSearch } from '../api/client'
import type { AutocompleteSuggestion } from '../types'

interface Props {
  value: string
  onChange: (value: string) => void
  onSelect: (suggestion: AutocompleteSuggestion) => void
  placeholder?: string
}

const DEBOUNCE_MS = 300

export function AutocompleteSearchBox({ value, onChange, onSelect, placeholder }: Props) {
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([])
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(-1)
  const boxRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (value.trim().length < 2) {
      setSuggestions([])
      return
    }
    debounceRef.current = setTimeout(() => {
      autocompleteSearch(value.trim())
        .then((list) => {
          setSuggestions(list)
          setOpen(list.length > 0)
          setHighlighted(-1)
        })
        .catch(() => setSuggestions([]))
    }, DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [value])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function pick(suggestion: AutocompleteSuggestion) {
    onSelect(suggestion)
    setOpen(false)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted((prev) => (prev + 1) % suggestions.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted((prev) => (prev <= 0 ? suggestions.length - 1 : prev - 1))
    } else if (e.key === 'Enter' && highlighted >= 0) {
      e.preventDefault()
      pick(suggestions[highlighted])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="autocomplete-box" ref={boxRef}>
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        onKeyDown={handleKeyDown}
        autoComplete="off"
      />
      {open && (
        <ul className="autocomplete-dropdown">
          {suggestions.map((s, i) => (
            <li key={`${s.address_name}-${i}`} className={i === highlighted ? 'autocomplete-item-active' : ''} onClick={() => pick(s)}>
              <span className="autocomplete-place-name">{s.place_name}</span>
              <span className="autocomplete-address">{s.road_address_name || s.address_name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
