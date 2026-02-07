import { useState, useEffect } from 'react'
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react'
import { useCurrency } from '../contexts/CurrencyContext'

interface CategoryData {
  name: string
  value: number
  color: string
}

interface MonthlyTrend {
  month: string
  income: number
  expenses: number
}

interface SummaryData {
  total_income: number
  total_expenses: number
  net_cashflow: number
  savings_rate: number
  symbol: string
}

export default function Analytics() {
  const [categoryData, setCategoryData] = useState<CategoryData[]>([])
  const [monthlyTrend, setMonthlyTrend] = useState<MonthlyTrend[]>([])
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'spending' | 'income'>('overview')
  const { currency, formatAmount } = useCurrency()

  useEffect(() => {
    fetchAnalytics()
  }, [currency])

  const fetchAnalytics = async () => {
    setLoading(true)
    try {
      const [summaryRes, cashflowRes, categoriesRes] = await Promise.all([
        fetch(`/api/v1/analytics/summary?user_id=1&display_currency=${currency}`),
        fetch(`/api/v1/analytics/cashflow?user_id=1&months=6&display_currency=${currency}`),
        fetch(`/api/v1/analytics/categories?user_id=1&months=6&display_currency=${currency}`),
      ])

      if (summaryRes.ok) {
        const data = await summaryRes.json()
        setSummary(data)
      }
      if (cashflowRes.ok) {
        const data = await cashflowRes.json()
        setMonthlyTrend(data.trend || [])
      }
      if (categoriesRes.ok) {
        const data = await categoriesRes.json()
        setCategoryData(data.categories || [])
      }
    } catch (err) {
      console.error('Failed to load analytics:', err)
    } finally {
      setLoading(false)
    }
  }

  const sym = summary?.symbol || '₹'

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-violet-500 border-t-transparent"></div>
      </div>
    )
  }

  const totalSpending = categoryData.reduce((s, c) => s + c.value, 0)

  return (
    <div className="h-full flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Analytics</h1>
          <p className="text-gray-400 text-sm">Financial insights and trends</p>
        </div>
        <div className="flex gap-2">
          {(['overview', 'spending', 'income'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                activeTab === tab ? 'bg-violet-600 text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 flex-shrink-0">
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">Total Income</p>
              <p className="text-2xl font-bold text-white mt-1">{formatAmount(summary?.total_income || 0, sym)}</p>
            </div>
            <div className="p-3 rounded-xl bg-emerald-500/10"><TrendingUp size={20} className="text-emerald-400" /></div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">Total Expenses</p>
              <p className="text-2xl font-bold text-white mt-1">{formatAmount(summary?.total_expenses || 0, sym)}</p>
            </div>
            <div className="p-3 rounded-xl bg-rose-500/10"><TrendingDown size={20} className="text-rose-400" /></div>
          </div>
        </div>
        <div className="card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">Savings Rate</p>
              <p className={`text-2xl font-bold mt-1 ${(summary?.savings_rate || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {(summary?.savings_rate || 0).toFixed(1)}%
              </p>
            </div>
            <div className="p-3 rounded-xl bg-violet-500/10"><DollarSign size={20} className="text-violet-400" /></div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
        {/* Spending Distribution Pie Chart */}
        <div className="card p-5 flex flex-col">
          <h3 className="text-sm font-semibold text-white mb-4">Spending Distribution</h3>
          <div className="flex-1 min-h-0">
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius="45%"
                    outerRadius="75%"
                    paddingAngle={3}
                    dataKey="value"
                    nameKey="name"
                  >
                    {categoryData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} stroke="transparent" />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333', borderRadius: '8px', fontSize: '12px' }}
                    formatter={(value: number, name: string) => [
                      `${formatAmount(value, sym)} (${totalSpending > 0 ? ((value / totalSpending) * 100).toFixed(1) : 0}%)`,
                      name,
                    ]}
                  />
                  <Legend
                    layout="horizontal"
                    verticalAlign="bottom"
                    wrapperStyle={{ fontSize: '11px', color: '#aaa' }}
                    formatter={(value: string, entry: any) => {
                      const item = categoryData.find((c) => c.name === value)
                      return `${value}  ${item ? formatAmount(item.value, sym) : ''}`
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                No spending data yet
              </div>
            )}
          </div>
        </div>

        {/* Monthly Income vs Expenses Bar Chart */}
        <div className="card p-5 flex flex-col">
          <h3 className="text-sm font-semibold text-white mb-4">Income vs Expenses</h3>
          <div className="flex-1 min-h-0">
            {monthlyTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlyTrend} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <XAxis dataKey="month" stroke="#444" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#444" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333', borderRadius: '8px', fontSize: '12px' }}
                    formatter={(value: number) => formatAmount(value, sym)}
                  />
                  <Bar dataKey="income" fill="#10b981" radius={[4, 4, 0, 0]} name="Income" />
                  <Bar dataKey="expenses" fill="#ef4444" radius={[4, 4, 0, 0]} name="Expenses" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                No monthly data yet
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
