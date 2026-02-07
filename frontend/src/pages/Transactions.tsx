import { useState, useEffect } from 'react'
import { Plus, Search, Filter, Download, Calendar, Tag, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { format } from 'date-fns'

interface Transaction {
  id: number
  description: string
  amount: number
  date: string
  type: 'income' | 'expense'
  category: string
}

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'income' | 'expense'>('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchTransactions()
  }, [])

  const fetchTransactions = async () => {
    try {
      const response = await fetch('/api/v1/transactions?limit=50')
      const data = await response.json()
      setTransactions(data.transactions || [])
    } catch (error) {
      console.error('Error fetching transactions:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredTransactions = transactions.filter((tx) => {
    const matchesSearch = tx.description.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = filter === 'all' || tx.type === filter
    return matchesSearch && matchesFilter
  })

  return (
    <div className="h-full flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Transactions</h1>
          <p className="text-gray-400 text-sm">Manage all your financial transactions</p>
        </div>
        <button className="btn btn-primary text-sm px-4 py-2">
          <Plus size={18} />
          Add New
        </button>
      </div>

      {/* Filters Toolbar */}
      <div className="card p-3 flex flex-col md:flex-row gap-4 items-center flex-shrink-0">
        <div className="flex-1 relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
          <input
            type="text"
            placeholder="Search description, category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input w-full pl-10 py-2 text-sm bg-white/5 border-white/10"
          />
        </div>
        
        <div className="flex gap-2">
          {['all', 'income', 'expense'].map((f) => (
             <button
               key={f}
               onClick={() => setFilter(f as any)}
               className={`px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize ${
                 filter === f
                   ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/20'
                   : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'
               }`}
             >
               {f}
             </button>
          ))}
          
          <button className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors">
            <Filter size={18} />
          </button>
          <button className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors">
            <Download size={18} />
          </button>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="card flex-1 overflow-hidden p-0 flex flex-col min-h-0">
        <div className="overflow-auto scrollbar-thin flex-1">
          <table className="table w-full">
            <thead className="sticky top-0 bg-[#13131f] z-10">
              <tr>
                <th className="pl-6 w-[40%] text-xs font-semibold text-gray-500 uppercase tracking-wider">Description</th>
                <th className="w-[20%] text-xs font-semibold text-gray-500 uppercase tracking-wider">Category</th>
                <th className="w-[20%] text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                <th className="text-right pr-6 w-[20%] text-xs font-semibold text-gray-500 uppercase tracking-wider">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan={4} className="text-center py-20">
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
                        <Search className="text-gray-500" size={24} />
                      </div>
                      <p className="text-gray-400 text-sm">No transactions found</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((tx) => (
                  <tr key={tx.id} className="group hover:bg-white/[0.02] transition-colors">
                    <td className="pl-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${
                          tx.type === 'income' ? 'bg-emerald-500/10' : 'bg-rose-500/10'
                        }`}>
                           {tx.type === 'income' ? <ArrowUpRight size={16} className="text-emerald-400"/> : <ArrowDownRight size={16} className="text-rose-400"/>}
                        </div>
                        <div>
                           <p className="text-white font-medium text-sm">{tx.description}</p>
                           <p className="text-xs text-gray-500 hidden sm:block">ID: #{tx.id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full bg-white/5 text-gray-300 text-xs font-medium border border-white/5">
                        {tx.category}
                      </span>
                    </td>
                    <td className="py-4">
                      <div className="flex items-center gap-2 text-gray-400 text-sm">
                        <Calendar size={14} />
                        <span>{format(new Date(tx.date), 'MMM dd')}</span>
                      </div>
                    </td>
                    <td className="text-right pr-6 py-4">
                      <span className={`font-bold text-sm ${
                          tx.type === 'income' ? 'text-emerald-400' : 'text-white'
                        }`}>
                        {tx.type === 'income' ? '+' : '-'}₹{tx.amount.toLocaleString()}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
