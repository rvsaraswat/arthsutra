import { useState } from 'react'
import { User, Bell, Shield, Database, Layout, Globe, Key, Smartphone, HardDrive, Download, Sliders } from 'lucide-react'

export default function Settings() {
  const [activeTab, setActiveTab] = useState('profile')
  const [settings, setSettings] = useState({
    currency: 'INR',
    language: 'en',
    notifications: true,
    darkMode: true,
    autoBackup: true,
  })

  const handleChange = (key: string, value: any) => {
    setSettings({ ...settings, [key]: value })
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'preferences', label: 'Preferences', icon: Sliders },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'data', label: 'Data & Privacy', icon: Database },
  ]

  return (
    <div className="flex h-full gap-6 animate-fade-in">
      {/* Sidebar Tabs */}
      <div className="w-64 flex-shrink-0">
        <h2 className="text-2xl font-bold text-white mb-6 px-2">Settings</h2>
        <div className="flex flex-col gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-medium ${
                  activeTab === tab.id
                    ? 'bg-violet-500/10 text-violet-400 border border-violet-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon size={18} />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 max-w-3xl overflow-y-auto pr-4 scrollbar-thin">
        {activeTab === 'profile' && (
          <div className="card space-y-6">
            <div className="flex items-center gap-4 border-b border-white/5 pb-6">
              <div className="w-16 h-16 rounded-full bg-violet-600 flex items-center justify-center text-2xl font-bold text-white">
                JD
              </div>
              <div>
                <h3 className="text-xl font-semibold text-white">John Doe</h3>
                <p className="text-gray-400 text-sm">Premium Member</p>
              </div>
              <button className="ml-auto btn btn-secondary text-xs py-2 px-4">Change Avatar</button>
            </div>
            
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">Full Name</label>
                <input
                  type="text"
                  className="input w-full"
                  defaultValue="John Doe"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">Email Address</label>
                <input
                  type="email"
                  className="input w-full"
                  defaultValue="john@example.com"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">Phone Number</label>
                <input
                  type="tel"
                  className="input w-full"
                  defaultValue="+91 98765 43210"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">Location</label>
                <input
                  type="text"
                  className="input w-full"
                  defaultValue="Mumbai, India"
                />
              </div>
            </div>
            
            <div className="pt-4 border-t border-white/5 flex justify-end">
              <button className="btn btn-primary">Save Changes</button>
            </div>
          </div>
        )}

        {activeTab === 'preferences' && (
          <div className="card space-y-6">
            <h3 className="text-xl font-semibold text-white mb-4">App Preferences</h3>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5">
                <div className="flex items-center gap-3">
                  <Globe className="text-gray-400" size={20} />
                  <div>
                    <p className="text-white font-medium">Currency</p>
                    <p className="text-xs text-gray-400">Default currency for transactions</p>
                  </div>
                </div>
                <select
                  className="input py-1 px-3 bg-black/20 border-white/10"
                  value={settings.currency}
                  onChange={(e) => handleChange('currency', e.target.value)}
                >
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                </select>
              </div>

              <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5">
                <div className="flex items-center gap-3">
                  <Layout className="text-gray-400" size={20} />
                  <div>
                    <p className="text-white font-medium">Language</p>
                    <p className="text-xs text-gray-400">Interface language</p>
                  </div>
                </div>
                <select
                  className="input py-1 px-3 bg-black/20 border-white/10"
                  value={settings.language}
                  onChange={(e) => handleChange('language', e.target.value)}
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                </select>
              </div>

              <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5">
                <div className="flex items-center gap-3">
                  <Bell className="text-gray-400" size={20} />
                  <div>
                    <p className="text-white font-medium">Notifications</p>
                    <p className="text-xs text-gray-400">Enable push notifications</p>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.notifications}
                    onChange={(e) => handleChange('notifications', e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-violet-600"></div>
                </label>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'security' && (
          <div className="card space-y-6">
            <h3 className="text-xl font-semibold text-white mb-4">Security</h3>
            
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-white/5 border border-white/5 cursor-pointer hover:bg-white/10 transition">
                <div className="flex items-center gap-3 mb-2">
                  <Key className="text-violet-400" size={20} />
                  <p className="text-white font-medium">Change Password</p>
                </div>
                <p className="text-xs text-gray-400 ml-8">Update your password regularly to keep your account secure</p>
              </div>

              <div className="p-4 rounded-xl bg-white/5 border border-white/5 cursor-pointer hover:bg-white/10 transition">
                <div className="flex items-center gap-3 mb-2">
                  <Smartphone className="text-violet-400" size={20} />
                  <p className="text-white font-medium">Two-Factor Authentication</p>
                </div>
                <p className="text-xs text-gray-400 ml-8">Add an extra layer of security to your account</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'data' && (
          <div className="card space-y-6">
            <h3 className="text-xl font-semibold text-white mb-4">Data Management</h3>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5">
                <div className="flex items-center gap-3">
                  <HardDrive className="text-gray-400" size={20} />
                  <div>
                    <p className="text-white font-medium">Auto Backup</p>
                    <p className="text-xs text-gray-400">Automatically backup your data every day</p>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.autoBackup}
                    onChange={(e) => handleChange('autoBackup', e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-violet-600"></div>
                </label>
              </div>

              <button className="w-full flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition text-left group">
                <div className="flex items-center gap-3">
                  <Download className="text-gray-400 group-hover:text-white" size={20} />
                  <div>
                    <p className="text-white font-medium">Export Data</p>
                    <p className="text-xs text-gray-400">Download all your financial data as CSV/JSON</p>
                  </div>
                </div>
              </button>

              <div className="mt-8 pt-6 border-t border-white/10">
                <button className="w-full py-3 text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl transition text-sm font-medium">
                  Delete Account
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
