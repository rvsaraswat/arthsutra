import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'

export default function Analytics() {
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    setTimeout(() => setLoading(false), 500)
  }, [])

  const categoryData = [
    { name: 'Food', value: 25000, color: '#ef4444' },
    { name: 'Transport', value: 15000, color: '#f59e0b' },
    { name: 'Shopping', value: 20000, color: '#10b981' },
    { name: 'Bills', value: 18000, color: '#3b82f6' },
    { name: 'Entertainment', value: 12000, color: '#8b5cf6' },
  ]

  const monthlyTrend = [
    { month: 'Jan', income: 50000, expenses: 35000 },
    { month: 'Feb', income: 52000, expenses: 38000 },
    { month: 'Mar', income: 50000, expenses: 34000 },
    { month: 'Apr', income: 54000, expenses: 36000 },
  ]

  if (loading) return null

  return (
    <div className="h-full flex flex-col gap-6 animate-fade-in">
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Analytics</h2>
          <p className="text-gray-400 text-sm">Financial insights and trends</p>
        </div>
        
        <div className="flex bg-white/5 p-1 rounded-xl">
          {['overview', 'spending', 'income'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all capitalize ${
                activeTab === tab 
                  ? 'bg-violet-600/20 text-violet-300 shadow-sm' 
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-shrink-0">
        <div className="card p-4">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-gray-400 text-xs uppercase tracking-wider font-semibold">Avg Income</p>
              <h3 className="text-2xl font-bold text-white mt-1">₹52,333</h3>
            </div>
            <div className="p-2 bg-emerald-500/10 rounded-lg">
              <TrendingUp className="text-emerald-400" size={18} />
            </div>
          </div>
          <div className="mt-2 text-xs text-emerald-400 flex items-center gap-1">
            <span>+8%</span>
            <span className="text-gray-500">vs last quarter</span>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-gray-400 text-xs uppercase tracking-wider font-semibold">Avg Expense</p>
              <h3 className="text-2xl font-bold text-white mt-1">₹35,333</h3>
            </div>
            <div className="p-2 bg-rose-500/10 rounded-lg">
              <TrendingDown className="text-rose-400" size={18} />
            </div>
          </div>
          <div className="mt-2 text-xs text-rose-400 flex items-center gap-1">
            <span>+5%</span>
            <span className="text-gray-500">vs last quarter</span>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-gray-400 text-xs uppercase tracking-wider font-semibold">Savings Rate</p>
              <h3 className="text-2xl font-bold text-white mt-1">32.5%</h3>
            </div>
            <div className="p-2 bg-violet-500/10 rounded-lg">
              <DollarSign className="text-violet-400" size={18} />
            </div>
          </div>
          <div className="mt-2 text-xs text-violet-400 flex items-center gap-1">
            <span>Target: 30%</span>
          </div>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
        <div className="card p-5 flex flex-col h-full">
          <h3 className="text-sm font-semibold text-white mb-4">Spending Distribution</h3>
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} stroke="rgba(0,0,0,0)" />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            {categoryData.slice(0, 4).map((cat) => (
              <div key={cat.name} className="flex items-center gap-2 text-xs text-gray-300">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat.color }} />
                <span className="flex-1">{cat.name}</span>
                <span className="font-medium">₹{(cat.value/1000).toFixed(1)}k</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-5 flex flex-col h-full">
          <h3 className="text-sm font-semibold text-white mb-4">Income vs Expenses</h3>
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyTrend} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                <XAxis dataKey="month" stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333', borderRadius: '8px' }}
                />
                <Bar dataKey="income" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={40} />
                <Bar dataKey="expenses" fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
