import { useState, useEffect, useRef } from 'react'
import { Plus, Building2, CreditCard, PiggyBank, TrendingUp, Landmark, Wallet, MoreVertical, X, Pencil, Trash2, RotateCcw, AlertTriangle, Check } from 'lucide-react'
import axios from 'axios'
import { useCurrency } from '../contexts/CurrencyContext'

interface Account {
  id: number
  name: string
  account_type: string
  institution: string | null
  account_number_masked: string | null
  currency: string
  balance: number
  is_active: boolean
  icon: string | null
  color: string | null
  notes: string | null
  transaction_count: number
}

interface AccountTypeGroups {
  [group: string]: string[]
}

const TYPE_ICONS: Record<string, any> = {
  savings: PiggyBank, current: Building2, salary: Building2,
  NRO: Landmark, NRE: Landmark, credit_card: CreditCard,
  FD: Landmark, RD: Landmark, PPF: Landmark, EPF: Landmark, NPS: Landmark,
  stocks: TrendingUp, mutual_funds: TrendingUp, bonds: TrendingUp, crypto: TrendingUp,
  wallet: Wallet, cash: Wallet, other: Wallet,
}

const TYPE_COLORS: Record<string, string> = {
  savings: '#10b981', current: '#3b82f6', salary: '#6366f1',
  NRO: '#f59e0b', NRE: '#f97316', credit_card: '#ef4444',
  FD: '#8b5cf6', RD: '#a855f7', PPF: '#14b8a6', EPF: '#06b6d4', NPS: '#0ea5e9',
  stocks: '#22c55e', mutual_funds: '#84cc16', bonds: '#eab308', crypto: '#f59e0b',
  wallet: '#64748b', cash: '#78716c', other: '#94a3b8',
}

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [groups, setGroups] = useState<AccountTypeGroups>({})
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const { formatAmount, currencyList, currency: globalCurrency } = useCurrency()

  // Dropdown menu state
  const [openMenuId, setOpenMenuId] = useState<number | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  // Edit modal
  const [editAccount, setEditAccount] = useState<Account | null>(null)
  const [editForm, setEditForm] = useState<Record<string, any>>({})

  // Delete confirmation
  const [confirmDelete, setConfirmDelete] = useState<Account | null>(null)

  // Show inactive toggle
  const [showInactive, setShowInactive] = useState(false)

  const [newAccount, setNewAccount] = useState({
    name: '', account_type: 'savings', institution: '', account_number_masked: '',
    currency: globalCurrency, balance: 0, notes: '',
  })

  useEffect(() => { fetchData() }, [])

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpenMenuId(null)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t) }
  }, [toast])

  const fetchData = async () => {
    try {
      const [acctRes, typesRes] = await Promise.all([
        axios.get('/api/v1/accounts?user_id=1'),
        axios.get('/api/v1/accounts/types'),
      ])
      setAccounts(acctRes.data.accounts || [])
      setGroups(typesRes.data.groups || {})
    } catch (err) {
      console.error('Failed to load accounts:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!newAccount.name.trim()) return
    try {
      await axios.post('/api/v1/accounts', { ...newAccount, user_id: 1 })
      setShowAddModal(false)
      setNewAccount({ name: '', account_type: 'savings', institution: '', account_number_masked: '', currency: globalCurrency, balance: 0, notes: '' })
      setToast({ message: 'Account created successfully', type: 'success' })
      fetchData()
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Failed to create account', type: 'error' })
    }
  }

  const handleDeactivate = async () => {
    if (!confirmDelete) return
    try {
      await axios.delete(`/api/v1/accounts/${confirmDelete.id}`)
      setConfirmDelete(null)
      setToast({ message: `"${confirmDelete.name}" deactivated`, type: 'success' })
      fetchData()
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Failed to deactivate', type: 'error' })
    }
  }

  const handleReactivate = async (acct: Account) => {
    try {
      await axios.put(`/api/v1/accounts/${acct.id}`, { is_active: true })
      setToast({ message: `"${acct.name}" reactivated`, type: 'success' })
      fetchData()
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Failed to reactivate', type: 'error' })
    }
  }

  const openEdit = (acct: Account) => {
    setEditAccount(acct)
    setEditForm({
      name: acct.name, account_type: acct.account_type, institution: acct.institution || '',
      account_number_masked: acct.account_number_masked || '', currency: acct.currency,
      notes: acct.notes || '',
    })
    setOpenMenuId(null)
  }

  const handleSaveEdit = async () => {
    if (!editAccount) return
    try {
      const updates: Record<string, any> = {}
      if (editForm.name !== editAccount.name) updates.name = editForm.name
      if (editForm.account_type !== editAccount.account_type) updates.account_type = editForm.account_type
      if (editForm.institution !== (editAccount.institution || '')) updates.institution = editForm.institution || null
      if (editForm.account_number_masked !== (editAccount.account_number_masked || '')) updates.account_number_masked = editForm.account_number_masked || null
      if (editForm.currency !== editAccount.currency) updates.currency = editForm.currency
      if (editForm.notes !== (editAccount.notes || '')) updates.notes = editForm.notes || null

      if (Object.keys(updates).length === 0) { setEditAccount(null); return }

      await axios.put(`/api/v1/accounts/${editAccount.id}`, updates)
      setEditAccount(null)
      setToast({ message: 'Account updated', type: 'success' })
      fetchData()
    } catch (err: any) {
      setToast({ message: err.response?.data?.detail || 'Failed to update', type: 'error' })
    }
  }

  const activeAccounts = accounts.filter((a) => a.is_active)
  const inactiveAccounts = accounts.filter((a) => !a.is_active)
  const totalBalance = activeAccounts.reduce((sum, a) => sum + a.balance, 0)

  const groupedAccounts: Record<string, Account[]> = {}
  for (const [groupName, types] of Object.entries(groups)) {
    const accts = activeAccounts.filter((a) => (types as string[]).includes(a.account_type))
    if (accts.length > 0) groupedAccounts[groupName] = accts
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-violet-500 border-t-transparent"></div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col gap-6 animate-fade-in">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-[100] px-5 py-3 rounded-xl shadow-2xl text-sm font-medium flex items-center gap-2 animate-fade-in ${toast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'}`}>
          {toast.type === 'success' ? <Check size={16} /> : <AlertTriangle size={16} />}
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Accounts</h1>
          <p className="text-gray-400 text-sm">Manage your bank accounts, cards, and investments</p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn btn-primary text-sm px-4 py-2">
          <Plus size={18} /> Add Account
        </button>
      </div>

      {/* Total Balance */}
      <div className="card p-6 bg-gradient-to-r from-violet-600/10 to-indigo-600/10 border-violet-500/20">
        <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-1">Total Balance</p>
        <p className="text-3xl font-bold text-white">{formatAmount(totalBalance)}</p>
        <p className="text-sm text-gray-400 mt-1">{activeAccounts.length} active account{activeAccounts.length !== 1 ? 's' : ''}</p>
      </div>

      {/* Accounts Grid */}
      <div className="flex-1 overflow-y-auto scrollbar-thin space-y-6">
        {Object.keys(groupedAccounts).length === 0 && inactiveAccounts.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4">
              <Building2 size={32} className="text-gray-500" />
            </div>
            <p className="text-gray-400 text-lg mb-2">No accounts yet</p>
            <p className="text-gray-500 text-sm mb-6">Add your bank accounts, credit cards, and investment accounts</p>
            <button onClick={() => setShowAddModal(true)} className="btn btn-primary text-sm px-6 py-2.5">
              <Plus size={18} /> Add Your First Account
            </button>
          </div>
        ) : (
          <>
            {Object.entries(groupedAccounts).map(([groupName, accts]) => (
              <div key={groupName}>
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">{groupName}</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {accts.map((acct) => {
                    const Icon = TYPE_ICONS[acct.account_type] || Wallet
                    const color = acct.color || TYPE_COLORS[acct.account_type] || '#6366f1'
                    return (
                      <div key={acct.id} className="card p-5 hover:bg-white/[0.03] transition-colors group relative">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div className="p-2.5 rounded-xl" style={{ backgroundColor: `${color}20` }}>
                              <Icon size={20} style={{ color }} />
                            </div>
                            <div>
                              <p className="text-white font-semibold text-sm">{acct.name}</p>
                              <p className="text-xs text-gray-500">
                                {acct.institution || acct.account_type}
                                {acct.account_number_masked && ` • ${acct.account_number_masked}`}
                              </p>
                            </div>
                          </div>
                          {/* ── Three-dot dropdown menu ── */}
                          <div className="relative" ref={openMenuId === acct.id ? menuRef : undefined}>
                            <button
                              onClick={(e) => { e.stopPropagation(); setOpenMenuId(openMenuId === acct.id ? null : acct.id) }}
                              className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-white/10 transition-all text-gray-500 hover:text-gray-300"
                            >
                              <MoreVertical size={16} />
                            </button>
                            {openMenuId === acct.id && (
                              <div className="absolute right-0 top-full mt-1 w-40 bg-[#1e1e30] border border-white/10 rounded-xl shadow-2xl shadow-black/50 z-50 py-1">
                                <button
                                  onClick={() => openEdit(acct)}
                                  className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-300 hover:bg-white/10 hover:text-white transition-colors"
                                >
                                  <Pencil size={14} /> Edit
                                </button>
                                <button
                                  onClick={() => { setConfirmDelete(acct); setOpenMenuId(null) }}
                                  className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
                                >
                                  <Trash2 size={14} /> Deactivate
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="mt-4">
                          <p className="text-lg font-bold text-white">{formatAmount(acct.balance)}</p>
                          <div className="flex items-center justify-between mt-1">
                            <span className="text-xs text-gray-500">{acct.currency}</span>
                            <span className="text-xs text-gray-500">{acct.transaction_count} transactions</span>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}

            {/* ── Inactive Accounts ── */}
            {inactiveAccounts.length > 0 && (
              <div>
                <button
                  onClick={() => setShowInactive(!showInactive)}
                  className="flex items-center gap-2 text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3 hover:text-gray-300 transition-colors"
                >
                  <span>Inactive ({inactiveAccounts.length})</span>
                  <span className="text-xs">{showInactive ? '▲' : '▼'}</span>
                </button>
                {showInactive && (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {inactiveAccounts.map((acct) => {
                      const Icon = TYPE_ICONS[acct.account_type] || Wallet
                      return (
                        <div key={acct.id} className="card p-5 opacity-50 hover:opacity-80 transition-opacity">
                          <div className="flex items-start justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <div className="p-2.5 rounded-xl bg-white/5"><Icon size={20} className="text-gray-500" /></div>
                              <div>
                                <p className="text-gray-300 font-semibold text-sm">{acct.name}</p>
                                <p className="text-xs text-gray-600">{acct.institution || acct.account_type}</p>
                              </div>
                            </div>
                            <button
                              onClick={() => handleReactivate(acct)}
                              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 transition-colors text-xs font-medium"
                            >
                              <RotateCcw size={13} /> Reactivate
                            </button>
                          </div>
                          <p className="text-lg font-bold text-gray-400 mt-4">{formatAmount(acct.balance)}</p>
                          <span className="text-xs text-gray-600">{acct.currency} · {acct.transaction_count} transactions</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* ──── Add Account Modal ──── */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowAddModal(false)}>
          <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-lg p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-white">Add New Account</h3>
              <button onClick={() => setShowAddModal(false)} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400"><X size={20} /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Account Name</label>
                <input type="text" placeholder="e.g. HDFC Savings" value={newAccount.name} onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })} className="input w-full" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Account Type</label>
                <select value={newAccount.account_type} onChange={(e) => setNewAccount({ ...newAccount, account_type: e.target.value })} className="input w-full bg-black/20">
                  {Object.entries(groups).map(([groupName, types]) => (
                    <optgroup key={groupName} label={groupName}>
                      {(types as string[]).map((t) => (<option key={t} value={t}>{t.replace(/_/g, ' ')}</option>))}
                    </optgroup>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Institution</label>
                  <input type="text" placeholder="e.g. HDFC Bank" value={newAccount.institution} onChange={(e) => setNewAccount({ ...newAccount, institution: e.target.value })} className="input w-full" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Account # (masked)</label>
                  <input type="text" placeholder="e.g. XXXX1234" value={newAccount.account_number_masked} onChange={(e) => setNewAccount({ ...newAccount, account_number_masked: e.target.value })} className="input w-full" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Currency</label>
                  <select value={newAccount.currency} onChange={(e) => setNewAccount({ ...newAccount, currency: e.target.value })} className="input w-full bg-black/20">
                    {currencyList.map((c) => (<option key={c.code} value={c.code}>{c.code} ({c.symbol})</option>))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Opening Balance</label>
                  <input type="number" step="0.01" value={newAccount.balance} onChange={(e) => setNewAccount({ ...newAccount, balance: parseFloat(e.target.value) || 0 })} className="input w-full" />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Notes (optional)</label>
                <input type="text" placeholder="Any notes..." value={newAccount.notes} onChange={(e) => setNewAccount({ ...newAccount, notes: e.target.value })} className="input w-full" />
              </div>
            </div>
            <div className="flex gap-3 mt-6 pt-4 border-t border-white/5">
              <button onClick={() => setShowAddModal(false)} className="flex-1 py-2.5 rounded-xl bg-white/5 text-gray-300 hover:bg-white/10 transition-colors font-medium text-sm">Cancel</button>
              <button onClick={handleCreate} disabled={!newAccount.name.trim()} className="flex-1 py-2.5 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition-colors font-medium text-sm disabled:opacity-40">Create Account</button>
            </div>
          </div>
        </div>
      )}

      {/* ──── Edit Account Modal ──── */}
      {editAccount && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setEditAccount(null)}>
          <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-lg p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-white flex items-center gap-2"><Pencil size={18} className="text-violet-400" /> Edit Account</h3>
              <button onClick={() => setEditAccount(null)} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400"><X size={20} /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Account Name</label>
                <input type="text" value={editForm.name || ''} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className="input w-full" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Account Type</label>
                <select value={editForm.account_type || 'savings'} onChange={(e) => setEditForm({ ...editForm, account_type: e.target.value })} className="input w-full bg-black/20">
                  {Object.entries(groups).map(([groupName, types]) => (
                    <optgroup key={groupName} label={groupName}>
                      {(types as string[]).map((t) => (<option key={t} value={t}>{t.replace(/_/g, ' ')}</option>))}
                    </optgroup>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Institution</label>
                  <input type="text" value={editForm.institution || ''} onChange={(e) => setEditForm({ ...editForm, institution: e.target.value })} className="input w-full" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Account # (masked)</label>
                  <input type="text" value={editForm.account_number_masked || ''} onChange={(e) => setEditForm({ ...editForm, account_number_masked: e.target.value })} className="input w-full" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Currency</label>
                  <select value={editForm.currency || 'INR'} onChange={(e) => setEditForm({ ...editForm, currency: e.target.value })} className="input w-full bg-black/20">
                    {currencyList.map((c) => (<option key={c.code} value={c.code}>{c.code} ({c.symbol})</option>))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Notes</label>
                  <input type="text" value={editForm.notes || ''} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} className="input w-full" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-6 pt-4 border-t border-white/5">
              <button onClick={() => setEditAccount(null)} className="flex-1 py-2.5 rounded-xl bg-white/5 text-gray-300 hover:bg-white/10 transition-colors font-medium text-sm">Cancel</button>
              <button onClick={handleSaveEdit} className="flex-1 py-2.5 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition-colors font-medium text-sm flex items-center justify-center gap-2">
                <Check size={16} /> Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ──── Deactivate Confirmation ──── */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setConfirmDelete(null)}>
          <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-md p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 rounded-full bg-red-500/10"><AlertTriangle size={24} className="text-red-400" /></div>
              <div>
                <h3 className="text-lg font-bold text-white">Deactivate Account</h3>
                <p className="text-sm text-gray-400">This account will be hidden but can be reactivated later.</p>
              </div>
            </div>
            <div className="bg-white/5 rounded-xl p-4 mb-4">
              <p className="text-white font-medium text-sm">{confirmDelete.name}</p>
              <p className="text-gray-400 text-xs mt-1">{confirmDelete.institution || confirmDelete.account_type} · {formatAmount(confirmDelete.balance)} · {confirmDelete.transaction_count} transactions</p>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setConfirmDelete(null)} className="flex-1 py-2.5 rounded-xl bg-white/5 text-gray-300 hover:bg-white/10 transition-colors font-medium text-sm">Cancel</button>
              <button onClick={handleDeactivate} className="flex-1 py-2.5 rounded-xl bg-red-600 text-white hover:bg-red-700 transition-colors font-medium text-sm flex items-center justify-center gap-2">
                <Trash2 size={16} /> Deactivate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
