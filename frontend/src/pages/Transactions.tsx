import { useState, useEffect } from 'react'
import {
  Plus, Search, Calendar, ArrowUpRight, ArrowDownRight, ArrowLeftRight,
  CreditCard, MapPin, Pencil, Trash2, RotateCcw, X, History, Archive,
  Check, AlertTriangle
} from 'lucide-react'
import { format } from 'date-fns'
import { useCurrency } from '../contexts/CurrencyContext'
import axios from 'axios'

interface Transaction {
  id: number
  description: string
  amount: number
  date: string
  type: 'income' | 'expense' | 'transfer'
  category: string
  merchant_name?: string
  merchant_category?: string
  transaction_method?: string
  account?: string
  account_id?: number
  currency?: string
  symbol?: string
  location?: string
  card_last_four?: string
  notes?: string
  tags?: string
  is_recurring?: boolean
  is_deleted?: boolean
  deleted_at?: string
}

interface AuditEntry {
  id: number
  action: string
  field_changed?: string
  old_value?: string
  new_value?: string
  timestamp: string
  notes?: string
}

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'income' | 'expense' | 'transfer'>('all')
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'active' | 'trash'>('active')
  const { currency, formatAmount, symbol: globalSymbol } = useCurrency()

  // Add new transaction
  const [showAddModal, setShowAddModal] = useState(false)
  const [addForm, setAddForm] = useState({
    description: '', amount: 0, transaction_type: 'expense' as 'income' | 'expense' | 'transfer',
    date: new Date().toISOString().split('T')[0], merchant_name: '', notes: ''
  })

  // Edit state
  const [editTx, setEditTx] = useState<Transaction | null>(null)
  const [editForm, setEditForm] = useState<Record<string, any>>({})

  // Delete confirm
  const [deleteTx, setDeleteTx] = useState<Transaction | null>(null)
  const [deleteReason, setDeleteReason] = useState('')

  // History
  const [historyTxId, setHistoryTxId] = useState<number | null>(null)
  const [historyEntries, setHistoryEntries] = useState<AuditEntry[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  useEffect(() => {
    fetchTransactions()
  }, [currency, tab])

  const fetchTransactions = async () => {
    setLoading(true)
    try {
      if (tab === 'trash') {
        const response = await axios.get(`/api/v1/transactions/trash?user_id=1&display_currency=${currency}`)
        setTransactions(response.data.transactions || [])
      } else {
        const response = await axios.get(`/api/v1/transactions?user_id=1&limit=500&display_currency=${currency}`)
        setTransactions(response.data.transactions || [])
      }
    } catch (error) {
      console.error('Error fetching transactions:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTx) return
    try {
      await axios.delete(`/api/v1/transactions/${deleteTx.id}?user_id=1${deleteReason ? `&reason=${encodeURIComponent(deleteReason)}` : ''}`)
      setDeleteTx(null)
      setDeleteReason('')
      fetchTransactions()
    } catch (err: any) {
      console.error('Delete failed:', err)
    }
  }

  const handleRestore = async (id: number) => {
    try {
      await axios.post(`/api/v1/transactions/${id}/restore?user_id=1`)
      fetchTransactions()
    } catch (err: any) {
      console.error('Restore failed:', err)
    }
  }

  const openEdit = (tx: Transaction) => {
    setEditTx(tx)
    setEditForm({
      description: tx.description,
      amount: Math.abs(tx.amount),
      transaction_type: tx.type,
      date: tx.date?.split('T')[0] || '',
      merchant_name: tx.merchant_name || '',
      notes: tx.notes || '',
    })
  }

  const handleSaveEdit = async () => {
    if (!editTx) return
    try {
      const updates: Record<string, any> = {}
      if (editForm.description !== editTx.description) updates.description = editForm.description
      if (editForm.merchant_name !== (editTx.merchant_name || '')) updates.merchant_name = editForm.merchant_name || null
      if (editForm.notes !== (editTx.notes || '')) updates.notes = editForm.notes || null
      if (editForm.transaction_type !== editTx.type) updates.transaction_type = editForm.transaction_type

      const newAmount = editForm.transaction_type === 'expense' ? -Math.abs(editForm.amount) : Math.abs(editForm.amount)
      if (Math.abs(newAmount - editTx.amount) > 0.001) updates.amount = newAmount

      if (editForm.date && editForm.date !== editTx.date?.split('T')[0]) {
        updates.date = new Date(editForm.date).toISOString()
      }

      if (Object.keys(updates).length === 0) {
        setEditTx(null)
        return
      }

      await axios.put(`/api/v1/transactions/${editTx.id}?user_id=1`, updates)
      setEditTx(null)
      fetchTransactions()
    } catch (err: any) {
      console.error('Edit failed:', err)
    }
  }

  const handleAddTransaction = async () => {
    if (!addForm.description.trim() || addForm.amount <= 0) return
    try {
      const amt = addForm.transaction_type === 'expense' ? -Math.abs(addForm.amount) : Math.abs(addForm.amount)
      await axios.post('/api/v1/transactions', {
        user_id: 1, description: addForm.description, amount: amt,
        currency: currency, transaction_type: addForm.transaction_type,
        date: new Date(addForm.date).toISOString(),
        merchant_name: addForm.merchant_name || null, notes: addForm.notes || null,
      })
      setShowAddModal(false)
      setAddForm({ description: '', amount: 0, transaction_type: 'expense', date: new Date().toISOString().split('T')[0], merchant_name: '', notes: '' })
      fetchTransactions()
    } catch (err: any) { console.error('Add failed:', err) }
  }

  const openHistory = async (txId: number) => {
    setHistoryTxId(txId)
    setHistoryLoading(true)
    try {
      const res = await axios.get(`/api/v1/transactions/${txId}/history?user_id=1`)
      setHistoryEntries(res.data.history || [])
    } catch (err) {
      console.error('Failed to load history:', err)
      setHistoryEntries([])
    } finally {
      setHistoryLoading(false)
    }
  }

  const filteredTransactions = transactions.filter((tx) => {
    const searchLower = search.toLowerCase()
    const matchesSearch =
      tx.description.toLowerCase().includes(searchLower) ||
      (tx.merchant_name && tx.merchant_name.toLowerCase().includes(searchLower)) ||
      (tx.account && tx.account.toLowerCase().includes(searchLower))
    const matchesFilter = filter === 'all' || tx.type === filter
    return matchesSearch && matchesFilter
  })

  const actionLabel = (a: string) => {
    const map: Record<string, string> = { create: '🆕 Created', edit: '✏️ Edited', delete: '🗑️ Deleted', restore: '♻️ Restored' }
    return map[a] || a
  }

  return (
    <div className="h-full flex flex-col gap-4 animate-fade-in overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Transactions</h1>
          <p className="text-gray-400 text-sm">Manage all your financial transactions</p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn btn-primary text-sm px-4 py-2">
          <Plus size={18} />
          Add New
        </button>
      </div>

      {/* Tabs: Active / Trash */}
      <div className="flex gap-2 flex-shrink-0">
        <button
          onClick={() => setTab('active')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            tab === 'active'
              ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/20'
              : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'
          }`}
        >
          <CreditCard size={16} />
          Active
        </button>
        <button
          onClick={() => setTab('trash')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            tab === 'trash'
              ? 'bg-amber-600 text-white shadow-lg shadow-amber-500/20'
              : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'
          }`}
        >
          <Archive size={16} />
          Trash
        </button>
      </div>

      {/* Filters Toolbar */}
      {tab === 'active' && (
        <div className="card p-3 flex flex-col md:flex-row gap-3 items-center flex-shrink-0">
          <div className="flex-1 relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
            <input
              type="text"
              placeholder="Search description, merchant, account..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input w-full pl-10 py-2 text-sm bg-white/5 border-white/10"
            />
          </div>
          <div className="flex gap-2 flex-shrink-0">
            {['all', 'income', 'expense', 'transfer'].map((f) => (
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
          </div>
        </div>
      )}

      {/* Transactions Table */}
      <div className="card flex-1 overflow-hidden p-0 flex flex-col min-h-0">
        <div className="overflow-auto scrollbar-thin flex-1">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-violet-500 border-t-transparent"></div>
            </div>
          ) : filteredTransactions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <div className="w-14 h-14 rounded-full bg-white/5 flex items-center justify-center">
                {tab === 'trash' ? <Archive className="text-gray-500" size={28} /> : <Search className="text-gray-500" size={28} />}
              </div>
              <p className="text-gray-400 text-sm">
                {tab === 'trash' ? 'No deleted transactions. Your financial data is safe.' : 'No transactions found'}
              </p>
            </div>
          ) : (
            <table className="table w-full">
              <thead className="sticky top-0 bg-[#13131f] z-10">
                <tr>
                  <th className="pl-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Description</th>
                  <th className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Category</th>
                  {tab === 'active' && <th className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Method</th>}
                  <th className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{tab === 'trash' ? 'Deleted' : 'Date'}</th>
                  <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Amount</th>
                  <th className="text-center pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredTransactions.map((tx) => (
                  <tr key={tx.id} className="group hover:bg-white/[0.02] transition-colors">
                    <td className="pl-6 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg flex-shrink-0 ${
                          tx.type === 'income' ? 'bg-emerald-500/10' : tx.type === 'transfer' ? 'bg-blue-500/10' : 'bg-rose-500/10'
                        }`}>
                          {tx.type === 'income' ? <ArrowUpRight size={16} className="text-emerald-400" /> : tx.type === 'transfer' ? <ArrowLeftRight size={16} className="text-blue-400" /> : <ArrowDownRight size={16} className="text-rose-400" />}
                        </div>
                        <div className="min-w-0">
                          <p className="text-white font-medium text-sm truncate">{tx.merchant_name || tx.description}</p>
                          {tx.merchant_name && tx.merchant_name !== tx.description && (
                            <p className="text-xs text-gray-500 truncate">{tx.description}</p>
                          )}
                          {tx.location && (
                            <p className="text-xs text-gray-600 flex items-center gap-1 mt-0.5">
                              <MapPin size={10} />{tx.location}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full bg-white/5 text-gray-300 text-xs font-medium border border-white/5">
                        {tx.merchant_category || tx.category || '\u2014'}
                      </span>
                    </td>
                    {tab === 'active' && (
                      <td className="py-3.5">
                        {tx.transaction_method ? (
                          <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                            <CreditCard size={12} />
                            {tx.transaction_method}
                            {tx.card_last_four && <span className="text-gray-600">\u2022{tx.card_last_four}</span>}
                          </span>
                        ) : (
                          <span className="text-gray-600 text-xs">\u2014</span>
                        )}
                      </td>
                    )}
                    <td className="py-3.5">
                      <div className="flex items-center gap-1.5 text-gray-400 text-sm">
                        <Calendar size={13} />
                        <span className="text-xs">
                          {tab === 'trash' && tx.deleted_at
                            ? format(new Date(tx.deleted_at), 'MMM dd, HH:mm')
                            : format(new Date(tx.date), 'MMM dd, yyyy')}
                        </span>
                      </div>
                    </td>
                    <td className="text-right py-3.5 pr-2">
                      <span className={`font-bold text-sm ${
                        tx.type === 'income' ? 'text-emerald-400' : tx.type === 'transfer' ? 'text-blue-400' : 'text-white'
                      }`}>
                        {tx.type === 'income' ? '+' : tx.type === 'transfer' ? '' : '-'}{formatAmount(Math.abs(tx.amount), tx.symbol || globalSymbol)}
                      </span>
                    </td>
                    <td className="text-center pr-4 py-3.5">
                      <div className="flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {tab === 'active' ? (
                          <>
                            <button
                              onClick={() => openEdit(tx)}
                              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-violet-400 transition-colors"
                              title="Edit"
                            >
                              <Pencil size={14} />
                            </button>
                            <button
                              onClick={() => openHistory(tx.id)}
                              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-blue-400 transition-colors"
                              title="History"
                            >
                              <History size={14} />
                            </button>
                            <button
                              onClick={() => setDeleteTx(tx)}
                              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-red-400 transition-colors"
                              title="Delete"
                            >
                              <Trash2 size={14} />
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleRestore(tx.id)}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors text-xs font-medium"
                          >
                            <RotateCcw size={13} />
                            Restore
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        {filteredTransactions.length > 0 && (
          <div className="px-6 py-3 border-t border-white/5 flex-shrink-0 flex items-center justify-between text-xs text-gray-500">
            <span>{filteredTransactions.length} transaction{filteredTransactions.length !== 1 ? 's' : ''}</span>
            {tab === 'trash' && (
              <span className="text-amber-400 flex items-center gap-1">
                <AlertTriangle size={12} />
                Deleted items can be restored at any time
              </span>
            )}
          </div>
        )}
      </div>

      {/* ──── Edit Modal ──── */}
      {editTx && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setEditTx(null)}>
          <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-lg p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Pencil size={18} className="text-violet-400" />
                Edit Transaction
              </h3>
              <button onClick={() => setEditTx(null)} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400"><X size={20} /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Description</label>
                <input type="text" value={editForm.description || ''} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} className="input w-full" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Amount</label>
                  <input type="number" step="0.01" value={editForm.amount || 0} onChange={(e) => setEditForm({ ...editForm, amount: parseFloat(e.target.value) || 0 })} className="input w-full" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Type</label>
                  <select value={editForm.transaction_type || 'expense'} onChange={(e) => setEditForm({ ...editForm, transaction_type: e.target.value })} className="input w-full bg-black/20">
                    <option value="expense">Expense</option>
                    <option value="income">Income</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Date</label>
                  <input type="date" value={editForm.date || ''} onChange={(e) => setEditForm({ ...editForm, date: e.target.value })} className="input w-full" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Merchant Name</label>
                  <input type="text" value={editForm.merchant_name || ''} onChange={(e) => setEditForm({ ...editForm, merchant_name: e.target.value })} className="input w-full" />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Notes</label>
                <input type="text" placeholder="Optional notes..." value={editForm.notes || ''} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} className="input w-full" />
              </div>
            </div>
            <div className="flex gap-3 mt-6 pt-4 border-t border-white/5">
              <button onClick={() => setEditTx(null)} className="flex-1 py-2.5 rounded-xl bg-white/5 text-gray-300 hover:bg-white/10 transition-colors font-medium text-sm">Cancel</button>
              <button onClick={handleSaveEdit} className="flex-1 py-2.5 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition-colors font-medium text-sm flex items-center justify-center gap-2">
                <Check size={16} /> Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──── Delete Confirmation Modal ──── */}
      {deleteTx && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setDeleteTx(null)}>
          <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-md p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 rounded-full bg-red-500/10"><Trash2 size={24} className="text-red-400" /></div>
              <div>
                <h3 className="text-lg font-bold text-white">Delete Transaction</h3>
                <p className="text-sm text-gray-400">Moves to trash. Can be restored later.</p>
              </div>
            </div>
            <div className="bg-white/5 rounded-xl p-4 mb-4">
              <p className="text-white font-medium text-sm">{deleteTx.merchant_name || deleteTx.description}</p>
              <p className="text-gray-400 text-xs mt-1">{formatAmount(Math.abs(deleteTx.amount), deleteTx.symbol || globalSymbol)} &bull; {format(new Date(deleteTx.date), 'MMM dd, yyyy')}</p>
            </div>
            <div className="mb-4">
              <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Reason (optional)</label>
              <input type="text" placeholder="Why are you deleting this?" value={deleteReason} onChange={(e) => setDeleteReason(e.target.value)} className="input w-full" />
            </div>
            <div className="flex gap-3">
              <button onClick={() => { setDeleteTx(null); setDeleteReason('') }} className="flex-1 py-2.5 rounded-xl bg-white/5 text-gray-300 hover:bg-white/10 transition-colors font-medium text-sm">Cancel</button>
              <button onClick={handleDelete} className="flex-1 py-2.5 rounded-xl bg-red-600 text-white hover:bg-red-700 transition-colors font-medium text-sm flex items-center justify-center gap-2">
                <Trash2 size={16} /> Move to Trash
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──── History Modal ──── */}
      {historyTxId !== null && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setHistoryTxId(null)}>
          <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-lg p-6 shadow-2xl max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5 flex-shrink-0">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <History size={18} className="text-blue-400" />
                Change History
              </h3>
              <button onClick={() => setHistoryTxId(null)} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400"><X size={20} /></button>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-thin space-y-3">
              {historyLoading ? (
                <div className="flex justify-center py-10"><div className="animate-spin rounded-full h-6 w-6 border-2 border-violet-500 border-t-transparent"></div></div>
              ) : historyEntries.length === 0 ? (
                <p className="text-center text-gray-500 py-10 text-sm">No history recorded</p>
              ) : (
                historyEntries.map((entry) => (
                  <div key={entry.id} className="bg-white/5 rounded-xl p-4 border border-white/5">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-white">{actionLabel(entry.action)}</span>
                      <span className="text-xs text-gray-500">{format(new Date(entry.timestamp), 'MMM dd, yyyy HH:mm')}</span>
                    </div>
                    {entry.field_changed && (
                      <div className="text-xs space-y-1">
                        <p className="text-gray-400">Field: <span className="text-gray-300 font-medium">{entry.field_changed}</span></p>
                        {entry.old_value && <p className="text-red-400/70">&minus; {entry.old_value}</p>}
                        {entry.new_value && <p className="text-emerald-400/70">+ {entry.new_value}</p>}
                      </div>
                    )}
                    {!entry.field_changed && entry.new_value && <p className="text-xs text-gray-400">{entry.new_value}</p>}
                    {entry.notes && <p className="text-xs text-gray-500 mt-1 italic">"{entry.notes}"</p>}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ──── Add Transaction Modal ──── */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowAddModal(false)}>
          <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-lg p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus size={18} className="text-violet-400" /> New Transaction
              </h3>
              <button onClick={() => setShowAddModal(false)} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400"><X size={20} /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Description</label>
                <input type="text" placeholder="e.g. Grocery shopping" value={addForm.description} onChange={(e) => setAddForm({ ...addForm, description: e.target.value })} className="input w-full" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Amount</label>
                  <input type="number" step="0.01" min="0" value={addForm.amount || ''} onChange={(e) => setAddForm({ ...addForm, amount: parseFloat(e.target.value) || 0 })} className="input w-full" placeholder="0.00" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Type</label>
                  <select value={addForm.transaction_type} onChange={(e) => setAddForm({ ...addForm, transaction_type: e.target.value as any })} className="input w-full bg-black/20">
                    <option value="expense">Expense</option>
                    <option value="income">Income</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Date</label>
                  <input type="date" value={addForm.date} onChange={(e) => setAddForm({ ...addForm, date: e.target.value })} className="input w-full" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Merchant</label>
                  <input type="text" placeholder="Optional" value={addForm.merchant_name} onChange={(e) => setAddForm({ ...addForm, merchant_name: e.target.value })} className="input w-full" />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Notes</label>
                <input type="text" placeholder="Optional" value={addForm.notes} onChange={(e) => setAddForm({ ...addForm, notes: e.target.value })} className="input w-full" />
              </div>
            </div>
            <div className="flex gap-3 mt-6 pt-4 border-t border-white/5">
              <button onClick={() => setShowAddModal(false)} className="flex-1 py-2.5 rounded-xl bg-white/5 text-gray-300 hover:bg-white/10 transition-colors font-medium text-sm">Cancel</button>
              <button
                onClick={handleAddTransaction}
                disabled={!addForm.description.trim() || addForm.amount <= 0}
                className="flex-1 py-2.5 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition-colors font-medium text-sm disabled:opacity-40 flex items-center justify-center gap-2"
              >
                <Check size={16} /> Add Transaction
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
