import { createContext, useContext } from 'react'
import { useArbitrageData } from './useArbitrageData'

type Ctx = ReturnType<typeof useArbitrageData>

const ArbitrageDataContext = createContext<Ctx | null>(null)

export function ArbitrageDataProvider({ children }: { children: React.ReactNode }) {
  const value = useArbitrageData()
  return <ArbitrageDataContext.Provider value={value}>{children}</ArbitrageDataContext.Provider>
}

export function useArbitrage() {
  const ctx = useContext(ArbitrageDataContext)
  if (!ctx) {
    throw new Error('useArbitrage must be used within ArbitrageDataProvider')
  }
  return ctx
}

