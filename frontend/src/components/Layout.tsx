import { Outlet, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Wallet, BarChart3, MessageSquare, Settings, Bell, Search, User } from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Transactions', href: '/transactions', icon: Wallet },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'AI Assistant', href: '/chat', icon: MessageSquare },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Layout() {
  const location = useLocation()

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
              <p className="text-sm font-medium text-white">John Doe</p>
              <p className="text-xs text-gray-500">Premium Member</p>
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
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 focus:bg-white/8 transition-all"
                />
              </div>
            </div>
            <div className="flex items-center gap-3 ml-6">
              <button className="p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors relative">
                <Bell size={20} className="text-gray-400" />
                <span className="absolute top-2 right-2 w-2 h-2 bg-violet-500 rounded-full ring-2 ring-[#0a0a0f]"></span>
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