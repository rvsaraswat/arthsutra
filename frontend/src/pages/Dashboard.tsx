import { useState, useEffect } from 'react'
import { ArrowUpRight, ArrowDownRight, ArrowLeftRight, Plus, TrendingUp, Percent } from 'lucide-react'
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { useNavigate } from 'react-router-dom'
import { useCurrency } from '../contexts/CurrencyContext'

interface Transaction {
  id: number
  description: string
  amount: number
  date: string
  type: 'income' | 'expense' | 'transfer'
  category: string
  merchant_name?: string
  account?: string
  currency?: string
  symbol?: string
  reference?: string
  notes?: string
  account_id?: number
}

interface AnalyticsData {
  total_income: number
  total_expenses: number
  net_cashflow: number
  savings_rate: number
  currency: string
  symbol: string
}

interface CashFlowPoint {
  month: string
  income: number
  expenses: number
}

export default function Dashboard() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [cashflow, setCashflow] = useState<CashFlowPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [hoveredTx, setHoveredTx] = useState<number | null>(null)
  const { currency, formatAmount } = useCurrency()
  const navigate = useNavigate()

  useEffect(() => {
    fetchDashboardData()
  }, [currency])

  const fetchDashboardData = async () => {
    try {
      const [txResponse, analyticsResponse, cashflowResponse] = await Promise.all([
        fetch(`/api/v1/transactions?user_id=1&limit=10&display_currency=${currency}`),
        fetch(`/api/v1/analytics/summary?user_id=1&display_currency=${currency}`),
        fetch(`/api/v1/analytics/cashflow?user_id=1&months=6&display_currency=${currency}`)
      ])

      const txData = await txResponse.json()
      const analyticsData = await analyticsResponse.json()

      setTransactions(txData.transactions || [])
      setAnalytics(analyticsData || null)

      if (cashflowResponse.ok) {
        const cfData = await cashflowResponse.json()
        setCashflow(cfData.trend || [])
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-violet-500 border-t-transparent"></div>
      </div>
    )
  }

  const sym = analytics?.symbol || '₹'

  return (
    <div className="h-full flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Dashboard</h1>
          <p className="text-gray-400 text-sm">Financial overview</p>
        </div>
        <button onClick={() => navigate('/transactions')} className="btn btn-primary text-sm px-4 py-2">
          <Plus size={18} />
          Add Transaction
        </button>
      </div>

      {/* Main Grid */}
      <div className="flex-1 grid grid-cols-12 gap-6 min-h-0">

        {/* Left Column */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-6 min-h-0">

          {/* Stats Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 flex-shrink-0">
            <div className="card-stat p-4">
              <span className="text-gray-400 text-xs font-semibold uppercase tracking-wider">Income</span>
              <div className="flex items-end justify-between mt-1">
                <span className="text-lg font-bold text-white truncate">{formatAmount(analytics?.total_income || 0, sym)}</span>
                <ArrowUpRight size={16} className="text-emerald-400 flex-shrink-0" />
              </div>
            </div>
            <div className="card-stat p-4">
              <span className="text-gray-400 text-xs font-semibold uppercase tracking-wider">Expenses</span>
              <div className="flex items-end justify-between mt-1">
                <span className="text-lg font-bold text-white truncate">{formatAmount(analytics?.total_expenses || 0, sym)}</span>
                <ArrowDownRight size={16} className="text-rose-400 flex-shrink-0" />
              </div>
            </div>
            <div className="card-stat p-4">
              <span className="text-gray-400 text-xs font-semibold uppercase tracking-wider">Net Flow</span>
              <div className="flex items-end justify-between mt-1">
                <span className={`text-lg font-bold truncate ${(analytics?.net_cashflow || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {formatAmount(analytics?.net_cashflow || 0, sym)}
                </span>
                <TrendingUp size={16} className="text-violet-400 flex-shrink-0" />
              </div>
            </div>
            <div className="card-stat p-4">
              <span className="text-gray-400 text-xs font-semibold uppercase tracking-wider">Savings Rate</span>
              <div className="flex items-end justify-between mt-1">
                <span className={`text-lg font-bold ${(analytics?.savings_rate || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {(analytics?.savings_rate || 0).toFixed(1)}%
                </span>
                <Percent size={16} className="text-emerald-400 flex-shrink-0" />
              </div>
            </div>
          </div>

          {/* Cash Flow Chart */}
          <div className="flex-1 min-h-0">
            <div className="card p-5 flex flex-col h-full">
              <h3 className="text-sm font-semibold text-white mb-4">Cash Flow Activity</h3>
              <div className="flex-1 min-h-0">
                {cashflow.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={cashflow} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorExpense" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="month" stroke="#444" fontSize={11} tickLine={false} axisLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333', borderRadius: '8px', fontSize: '12px' }}
                        itemStyle={{ color: '#fff' }}
                        formatter={(value: number) => formatAmount(value, sym)}
                      />
                      <Area type="monotone" dataKey="income" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorIncome)" name="Income" />
                      <Area type="monotone" dataKey="expenses" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#colorExpense)" name="Expenses" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                    No cash flow data yet. Import some transactions to see your trends.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Recent Transactions */}
        <div className="col-span-12 lg:col-span-4 flex flex-col min-h-0">
          <div className="card flex-1 flex flex-col p-5 overflow-hidden">
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <h3 className="text-lg font-semibold text-white">Recent Transactions</h3>
              <button onClick={() => navigate('/transactions')} className="text-xs text-violet-400 hover:text-violet-300 cursor-pointer">
                View All
              </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 scrollbar-thin space-y-3">
              {transactions.length === 0 ? (
                <div className="text-center text-gray-500 text-sm py-10">No recent transactions</div>
              ) : (
                transactions.map((tx) => (
                  <div
                    key={tx.id}
                    className="relative flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors group cursor-pointer"
                    onMouseEnter={() => setHoveredTx(tx.id)}
                    onMouseLeave={() => setHoveredTx(null)}
                    onClick={() => navigate('/transactions')}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${tx.type === 'income' ? 'bg-emerald-500/10' : tx.type === 'transfer' ? 'bg-blue-500/10' : 'bg-rose-500/10'}`}>
                        {tx.type === 'income' ? <ArrowUpRight size={16} className="text-emerald-400" /> : tx.type === 'transfer' ? <ArrowLeftRight size={16} className="text-blue-400" /> : <ArrowDownRight size={16} className="text-rose-400" />}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white truncate max-w-[140px]">{tx.merchant_name || tx.description}</p>
                        <p className="text-xs text-gray-500">{tx.account || tx.category}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-bold ${tx.type === 'income' ? 'text-emerald-400' : tx.type === 'transfer' ? 'text-blue-400' : 'text-white'}`}>
                        {tx.type === 'income' ? '+' : tx.type === 'transfer' ? '' : '-'}{formatAmount(Math.abs(tx.amount), tx.symbol || sym)}
                      </p>
                      <p className="text-[10px] text-gray-500">
                        {new Date(tx.date).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}
                      </p>
                    </div>

                    {/* Hover tooltip */}
                    {hoveredTx === tx.id && (
                      <div className="absolute left-0 right-0 bottom-full mb-2 z-50 pointer-events-none">
                        <div className="bg-[#1e1e30] border border-white/10 rounded-xl p-3 shadow-2xl shadow-black/60 text-xs mx-2">
                          <p className="text-white font-medium mb-1">{tx.description}</p>
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-400">
                            <span>Amount:</span>
                            <span className="text-white">{formatAmount(Math.abs(tx.amount), tx.symbol || sym)}</span>
                            <span>Date:</span>
                            <span className="text-white">{new Date(tx.date).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}</span>
                            <span>Type:</span>
                            <span className={tx.type === 'income' ? 'text-emerald-400' : tx.type === 'transfer' ? 'text-blue-400' : 'text-rose-400'}>{tx.type}</span>
                            {tx.account && <><span>Account:</span><span className="text-white">{tx.account}</span></>}
                            {tx.reference && <><span>Reference:</span><span className="text-white truncate">{tx.reference}</span></>}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
