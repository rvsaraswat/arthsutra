import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Wallet, BarChart3, MessageSquare, Settings, Bell, Search, User, Upload, Building2, ChevronDown } from 'lucide-react'
import { useCurrency } from '../contexts/CurrencyContext'
import { useState, useRef, useEffect } from 'react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Transactions', href: '/transactions', icon: Wallet },
  { name: 'Import', href: '/import', icon: Upload },
  { name: 'Accounts', href: '/accounts', icon: Building2 },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'AI Assistant', href: '/chat', icon: MessageSquare },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { currency, symbol, currencyList, setCurrency } = useCurrency()
  const [showCurrencyDropdown, setShowCurrencyDropdown] = useState(false)
  const [currencySearch, setCurrencySearch] = useState('')
  const [globalSearch, setGlobalSearch] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowCurrencyDropdown(false)
        setCurrencySearch('')
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const filteredCurrencies = currencyList.filter(
    (c) =>
      c.code.toLowerCase().includes(currencySearch.toLowerCase()) ||
      c.name.toLowerCase().includes(currencySearch.toLowerCase())
  )

  return (
    <div className="h-screen bg-[#0a0a0f] flex overflow-hidden">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-72 bg-gradient-to-b from-[#0f0f1a] to-[#1a1a2e] border-r border-white/5 z-50">
        <div className="p-8">
          {/* Logo */}
          <div className="mb-12">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                <Wallet className="text-white" size={22} strokeWidth={2.5} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">
                  Arthsutra
                </h1>
                <p className="text-xs text-gray-500 font-medium">Financial Intelligence</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="space-y-1.5">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href

              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all duration-200 group ${
                    isActive
                      ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/30'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Icon size={20} strokeWidth={2} className={isActive ? 'text-white' : 'text-gray-500 group-hover:text-violet-400'} />
                  <span className="font-medium text-[15px]">{item.name}</span>
                </Link>
              )
            })}
          </nav>
        </div>

        {/* User Profile at Bottom */}
        <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-white/5">
          <div className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 transition-colors cursor-pointer">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center">
              <User size={20} className="text-white" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-white">{localStorage.getItem('user_name') || 'User'}</p>
              <p className="text-xs text-gray-500">Arthsutra</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="ml-72 flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Bar */}
        <header className="sticky top-0 z-40 border-b border-white/5 bg-[#0a0a0f]/80 backdrop-blur-xl shrink-0">
          <div className="flex items-center justify-between px-8 py-5">
            <div className="flex-1 max-w-2xl">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                <input
                  type="text"
                  placeholder="Search transactions, categories..."
                  value={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && globalSearch.trim()) { navigate('/transactions'); setGlobalSearch('') } }}
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 focus:bg-white/8 transition-all"
                />
              </div>
            </div>
            <div className="flex items-center gap-3 ml-6">
              {/* Currency Selector */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setShowCurrencyDropdown(!showCurrencyDropdown)}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition-colors text-sm"
                >
                  <span className="text-violet-400 font-bold text-base">{symbol}</span>
                  <span className="text-gray-300 font-medium">{currency}</span>
                  <ChevronDown size={14} className={`text-gray-500 transition-transform ${showCurrencyDropdown ? 'rotate-180' : ''}`} />
                </button>

                {showCurrencyDropdown && (
                  <div className="absolute right-0 top-full mt-2 w-72 bg-[#1a1a2e] border border-white/10 rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-50">
                    <div className="p-3 border-b border-white/5">
                      <input
                        type="text"
                        placeholder="Search currencies..."
                        value={currencySearch}
                        onChange={(e) => setCurrencySearch(e.target.value)}
                        className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50"
                        autoFocus
                      />
                    </div>
                    <div className="max-h-64 overflow-y-auto scrollbar-thin">
                      {filteredCurrencies.map((c) => (
                        <button
                          key={c.code}
                          onClick={() => {
                            setCurrency(c.code)
                            setShowCurrencyDropdown(false)
                            setCurrencySearch('')
                          }}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                            c.code === currency
                              ? 'bg-violet-600/20 text-violet-300'
                              : 'text-gray-300 hover:bg-white/5 hover:text-white'
                          }`}
                        >
                          <span className="w-8 text-center font-bold text-base">{c.symbol}</span>
                          <span className="font-medium">{c.code}</span>
                          <span className="text-gray-500 text-xs ml-auto truncate max-w-[120px]">{c.name}</span>
                        </button>
                      ))}
                      {filteredCurrencies.length === 0 && (
                        <div className="px-4 py-6 text-center text-gray-500 text-sm">No currencies found</div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <button className="p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors relative" title="Notifications">
                <Bell size={20} className="text-gray-400" />
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-hidden p-6 relative">
          <Outlet />
        </main>
      </div>
    </div>
  )
}