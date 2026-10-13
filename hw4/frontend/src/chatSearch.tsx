import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { PageResults } from './api'

// Holds the latest chat search results so the Products page can show them.
type ChatSearchState = {
  results: PageResults | null
  showResults: (results: PageResults) => void
  clearResults: () => void
}

const ChatSearchContext = createContext<ChatSearchState | null>(null)

export function ChatSearchProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<PageResults | null>(null)
  const clearResults = useCallback(() => setResults(null), [])
  const value = useMemo(() => ({ results, showResults: setResults, clearResults }), [results, clearResults])
  return <ChatSearchContext.Provider value={value}>{children}</ChatSearchContext.Provider>
}

export function useChatSearch(): ChatSearchState {
  const ctx = useContext(ChatSearchContext)
  if (!ctx) throw new Error('useChatSearch must be used inside ChatSearchProvider')
  return ctx
}
