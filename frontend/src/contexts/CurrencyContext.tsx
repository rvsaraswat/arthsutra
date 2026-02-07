import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import axios from 'axios'

interface CurrencyInfo {
  code: string
  symbol: string
  name: string
}

interface CurrencyContextType {
  currency: string
  symbol: string
  currencyList: CurrencyInfo[]
  setCurrency: (code: string) => void
  formatAmount: (amount: number, overrideSymbol?: string) => string
  loading: boolean
}

const CurrencyContext = createContext<CurrencyContextType>({
  currency: 'INR',
  symbol: '₹',
  currencyList: [],
  setCurrency: () => {},
  formatAmount: (amount) => `₹${Math.abs(amount).toLocaleString()}`,
  loading: true,
})

export const useCurrency = () => useContext(CurrencyContext)

interface CurrencyProviderProps {
  children: ReactNode
}

export function CurrencyProvider({ children }: CurrencyProviderProps) {
  const [currency, setCurrencyState] = useState(() => localStorage.getItem('preferred_currency') || 'INR')
  const [symbol, setSymbol] = useState(() => localStorage.getItem('preferred_symbol') || '₹')
  const [currencyList, setCurrencyList] = useState<CurrencyInfo[]>([])
  const [loading, setLoading] = useState(true)

  // Fetch supported currencies and user preferences on mount
  useEffect(() => {
    const init = async () => {
      try {
        const [currenciesRes, prefsRes] = await Promise.all([
          axios.get('/api/v1/currency/supported'),
          axios.get('/api/v1/user/preferences?user_id=1'),
        ])

        const list: CurrencyInfo[] = currenciesRes.data.currencies || []
        setCurrencyList(list)

        const prefs = prefsRes.data
        if (prefs.preferred_currency) {
          setCurrencyState(prefs.preferred_currency)
          setSymbol(prefs.symbol || '₹')
          localStorage.setItem('preferred_currency', prefs.preferred_currency)
          localStorage.setItem('preferred_symbol', prefs.symbol || '₹')
        }
      } catch (err) {
        console.error('Failed to load currency preferences:', err)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const setCurrency = useCallback(async (code: string) => {
    const upper = code.toUpperCase()
    setCurrencyState(upper)
    localStorage.setItem('preferred_currency', upper)

    // Find symbol from list
    const info = currencyList.find((c) => c.code === upper)
    const newSymbol = info?.symbol || upper
    setSymbol(newSymbol)
    localStorage.setItem('preferred_symbol', newSymbol)

    // Persist to backend
    try {
      await axios.put(`/api/v1/user/preferences?preferred_currency=${upper}&user_id=1`)
    } catch (err) {
      console.error('Failed to save currency preference:', err)
    }
  }, [currencyList])

  const formatAmount = useCallback((amount: number, overrideSymbol?: string) => {
    const sym = overrideSymbol || symbol
    const abs = Math.abs(amount)
    const sign = amount < 0 ? '-' : ''
    
    // No-decimal currencies
    const noDecimal = new Set(['JPY', 'KRW', 'VND', 'CLP', 'IDR', 'HUF'])
    const formatted = noDecimal.has(currency)
      ? abs.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })
      : abs.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

    return `${sign}${sym}${formatted}`
  }, [symbol, currency])

  return (
    <CurrencyContext.Provider value={{ currency, symbol, currencyList, setCurrency, formatAmount, loading }}>
      {children}
    </CurrencyContext.Provider>
  )
}

export default CurrencyContext
