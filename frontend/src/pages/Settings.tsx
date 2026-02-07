import { useState, useEffect } from 'react'
import { User, Shield, Download, Trash2, Check, AlertTriangle, Globe } from 'lucide-react'
import { useCurrency } from '../contexts/CurrencyContext'

export default function Settings() {
  const { currency, setCurrency, currencyList } = useCurrency()
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const [profile, setProfile] = useState({ name: '', email: '' })
  const [exporting, setExporting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  useEffect(() => {
    // Load profile from localStorage or defaults
    setProfile({
      name: localStorage.getItem('user_name') || 'User',
      email: localStorage.getItem('user_email') || '',
    })
  }, [])

  useEffect(() => {
    if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t) }
  }, [toast])

  const handleSaveProfile = () => {
    localStorage.setItem('user_name', profile.name)
    localStorage.setItem('user_email', profile.email)
    setToast({ message: 'Profile saved', type: 'success' })
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const res = await fetch('/api/v1/transactions/export?user_id=1')
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `arthsutra_export_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      URL.revokeObjectURL(url)
      setToast({ message: 'Transactions exported successfully', type: 'success' })
    } catch (err) {
      setToast({ message: 'Failed to export data', type: 'error' })
    } finally {
      setExporting(false)
    }
  }

  const handleDeleteAllData = async () => {
    setShowDeleteConfirm(false)
    try {
      const res = await fetch('/api/v1/admin/wipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: true }),
      })

      if (!res.ok) {
        // backend returns JSON errors but fall back to text
        const msg = await res.text()
        throw new Error(msg || 'Wipe failed')
      }

      setToast({ message: 'All data deleted. Ready to re-upload.', type: 'success' })
    } catch (err) {
      setToast({ message: 'Failed to delete data', type: 'error' })
    }
  }

  return (
    <div className="h-full flex flex-col gap-6 animate-fade-in max-w-3xl">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-[100] px-5 py-3 rounded-xl shadow-2xl text-sm font-medium flex items-center gap-2 animate-fade-in ${toast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'}`}>
          {toast.type === 'success' ? <Check size={16} /> : <AlertTriangle size={16} />}
          {toast.message}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-gray-400 text-sm">Manage your preferences</p>
      </div>

      {/* Profile Section */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-violet-500/10"><User size={20} className="text-violet-400" /></div>
          <h2 className="text-lg font-semibold text-white">Profile</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Full Name</label>
            <input
              type="text"
              value={profile.name}
              onChange={(e) => setProfile({ ...profile, name: e.target.value })}
              className="input w-full"
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Email</label>
            <input
              type="email"
              value={profile.email}
              onChange={(e) => setProfile({ ...profile, email: e.target.value })}
              className="input w-full"
              placeholder="your@email.com"
            />
          </div>
          <button
            onClick={handleSaveProfile}
            className="px-6 py-2.5 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition-colors font-medium text-sm"
          >
            Save Changes
          </button>
        </div>
      </div>

      {/* Currency Preference */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-emerald-500/10"><Globe size={20} className="text-emerald-400" /></div>
          <h2 className="text-lg font-semibold text-white">Currency</h2>
        </div>
        <div>
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5 block">Display Currency</label>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="input w-full max-w-sm bg-black/20"
          >
            {currencyList.map((c) => (
              <option key={c.code} value={c.code}>{c.symbol} {c.code} — {c.name}</option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-2">All amounts will be displayed in this currency. Conversion is automatic.</p>
        </div>
      </div>

      {/* Security - placeholder */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-blue-500/10"><Shield size={20} className="text-blue-400" /></div>
          <h2 className="text-lg font-semibold text-white">Security</h2>
        </div>
        <p className="text-sm text-gray-500">Authentication and password management will be available in a future update. Your data is stored locally on this device.</p>
      </div>

      {/* Data Management */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-amber-500/10"><Download size={20} className="text-amber-400" /></div>
          <h2 className="text-lg font-semibold text-white">Data Management</h2>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/5">
            <div>
              <p className="text-sm font-medium text-white">Export Transactions</p>
              <p className="text-xs text-gray-500">Download all your transactions as a CSV file</p>
            </div>
            <button
              onClick={handleExport}
              disabled={exporting}
              className="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors text-sm font-medium disabled:opacity-50"
            >
              {exporting ? 'Exporting...' : 'Export CSV'}
            </button>
          </div>

          <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-red-500/10">
            <div>
              <p className="text-sm font-medium text-red-400">Delete All Data</p>
              <p className="text-xs text-gray-500">Permanently remove all accounts and transactions</p>
            </div>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-4 py-2 rounded-lg bg-red-600/10 text-red-400 border border-red-500/20 hover:bg-red-600/20 transition-colors text-sm font-medium"
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setShowDeleteConfirm(false)}>
          <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-md p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 rounded-full bg-red-500/10"><AlertTriangle size={24} className="text-red-400" /></div>
              <div>
                <h3 className="text-lg font-bold text-white">Delete All Data?</h3>
                <p className="text-sm text-gray-400">This action cannot be undone.</p>
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => setShowDeleteConfirm(false)} className="flex-1 py-2.5 rounded-xl bg-white/5 text-gray-300 hover:bg-white/10 transition-colors font-medium text-sm">Cancel</button>
              <button onClick={handleDeleteAllData} className="flex-1 py-2.5 rounded-xl bg-red-600 text-white hover:bg-red-700 transition-colors font-medium text-sm flex items-center justify-center gap-2">
                <Trash2 size={16} /> Delete Everything
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
