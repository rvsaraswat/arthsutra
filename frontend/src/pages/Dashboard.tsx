import { useState, useEffect } from 'react'
import { ArrowUpRight, ArrowDownRight, Plus } from 'lucide-react'
import { LineChart, Line, AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface Transaction {
  id: number
  description: string
  amount: number
  date: string
  type: 'income' | 'expense'
  category: string
}

interface AnalyticsData {
  total_income: number
  total_expenses: number
  net_cashflow: number
  savings_rate: number
}

export default function Dashboard() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      const [txResponse, analyticsResponse] = await Promise.all([
        fetch('/api/v1/transactions?limit=10'),
        fetch('/api/v1/analytics/summary?days=30')
      ])

      const txData = await txResponse.json()
      const analyticsData = await analyticsResponse.json()

      setTransactions(txData.transactions || [])
      setAnalytics(analyticsData || null)
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const cashflowData = [
    { month: 'Jan', income: 50000, expenses: 35000 },
    { month: 'Feb', income: 52000, expenses: 38000 },
    { month: 'Mar', income: 50000, expenses: 34000 },
    { month: 'Apr', income: 54000, expenses: 36000 },
    { month: 'May', income: 53000, expenses: 35000 },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-violet-500 border-t-transparent"></div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Welcome back, John</h1>
          <p className="text-gray-400 text-sm">Financial overview for June 2026</p>
        </div>
        <button className="btn btn-primary text-sm px-4 py-2">
          <Plus size={18} />
          Add Transaction
        </button>
      </div>

      {/* Main Content Grid */}
      <div className="flex-1 grid grid-cols-12 gap-6 min-h-0">
        
        {/* Left Column: Stats & Charts (2/3 width) */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-6 min-h-0">
          
          {/* Quick Stats Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 flex-shrink-0">
             <div className="card-stat p-4">
               <span className="text-gray-400 text-xs font-semibold uppercase tracking-wider">Income</span>
               <div className="flex items-end justify-between mt-1">
                 <span className="text-xl font-bold text-white">₹3.2L</span>
                 <div className="flex items-center text-emerald-400 text-xs">
                    <ArrowUpRight size={14} />
                    <span>12%</span>
                 </div>
               </div>
             </div>
             
             <div className="card-stat p-4">
               <span className="text-gray-400 text-xs font-semibold uppercase tracking-wider">Expenses</span>
               <div className="flex items-end justify-between mt-1">
                 <span className="text-xl font-bold text-white">₹2.1L</span>
                 <div className="flex items-center text-rose-400 text-xs">
                    <ArrowDownRight size={14} />
                    <span>8%</span>
                 </div>
               </div>
             </div>

             <div className="card-stat p-4">
               <span className="text-gray-400 text-xs font-semibold uppercase tracking-wider">Savings</span>
               <div className="flex items-end justify-between mt-1">
                 <span className="text-xl font-bold text-white">₹1.1L</span>
                 <div className="flex items-center text-violet-400 text-xs">
                    <ArrowUpRight size={14} />
                    <span>15%</span>
                 </div>
               </div>
             </div>

             <div className="card-stat p-4">
               <span className="text-gray-400 text-xs font-semibold uppercase tracking-wider">Invested</span>
               <div className="flex items-end justify-between mt-1">
                 <span className="text-xl font-bold text-white">₹85k</span>
                 <div className="flex items-center text-emerald-400 text-xs">
                    <ArrowUpRight size={14} />
                    <span>5%</span>
                 </div>
               </div>
             </div>
          </div>

          {/* Charts Area */}
          <div className="flex-1 grid grid-cols-1 gap-6 min-h-0">
            <div className="card p-5 flex flex-col h-full">
              <h3 className="text-sm font-semibold text-white mb-4">Cash Flow Activity</h3>
              <div className='flex-1 min-h-0'>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={cashflowData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorExpense" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="month" stroke="#444" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333', borderRadius: '8px', fontSize: '12px' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Area type="monotone" dataKey="income" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorIncome)" />
                    <Area type="monotone" dataKey="expenses" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#colorExpense)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            <div className="card p-5 flex flex-col h-full lg:hidden">
               {/* Mobile/Tablet Fallback graph if strictly needed, mostly hidden on large screens to save space */}
               <h3 className="text-sm font-semibold text-white mb-4">Investment Growth</h3>
               <div className='flex-1 min-h-0'>
                <ResponsiveContainer width="100%" height="100%">
                   <LineChart data={cashflowData}>
                      <Line type="monotone" dataKey="income" stroke="#8b5cf6" strokeWidth={2} dot={false} />
                   </LineChart>
                </ResponsiveContainer>
               </div>
            </div>

          </div>
        </div>

        {/* Right Column: Recent Transactions (1/3 width) */}
        <div className="col-span-12 lg:col-span-4 flex flex-col min-h-0">
          <div className="card flex-1 flex flex-col p-5 overflow-hidden">
             <div className="flex items-center justify-between mb-4 flex-shrink-0">
               <h3 className="text-lg font-semibold text-white">Recent Transactions</h3>
               <button className="text-xs text-violet-400 hover:text-violet-300">View All</button>
             </div>
             
             <div className="flex-1 overflow-y-auto pr-2 scrollbar-thin space-y-3">
               {transactions.length === 0 ? (
                 <div className="text-center text-gray-500 text-sm py-10">No recent transactions</div>
               ) : (
                 transactions.map((tx) => (
                   <div key={tx.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors group cursor-pointer">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${
                          tx.type === 'income' ? 'bg-emerald-500/10' : 'bg-rose-500/10'
                        }`}>
                          {tx.type === 'income' ? (
                            <ArrowUpRight size={16} className="text-emerald-400" />
                          ) : (
                            <ArrowDownRight size={16} className="text-rose-400" />
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white truncate max-w-[120px]">{tx.description}</p>
                          <p className="text-xs text-gray-500">{tx.category}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-bold ${
                          tx.type === 'income' ? 'text-emerald-400' : 'text-white'
                        }`}>
                          {tx.type === 'income' ? '+' : '-'}₹{tx.amount.toLocaleString()}
                        </p>
                        <p className="text-[10px] text-gray-500">
                          {new Date(tx.date).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}
                        </p>
                      </div>
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
