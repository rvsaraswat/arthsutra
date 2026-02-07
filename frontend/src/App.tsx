import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { CurrencyProvider } from './contexts/CurrencyContext'
import Dashboard from './pages/Dashboard'
import Transactions from './pages/Transactions'
import Analytics from './pages/Analytics'
import Chat from './pages/Chat'
import Settings from './pages/Settings'
import Import from './pages/Import'
import Accounts from './pages/Accounts'
import Layout from './components/Layout'

function App() {
  return (
    <CurrencyProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="transactions" element={<Transactions />} />
            <Route path="import" element={<Import />} />
            <Route path="accounts" element={<Accounts />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="chat" element={<Chat />} />
            <Route path="settings" element={<Settings />} />
            <Route path="*" element={<div className="flex items-center justify-center h-full"><div className="text-center"><h1 className="text-4xl font-bold text-white mb-2">404</h1><p className="text-gray-400">Page not found</p></div></div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </CurrencyProvider>
  )
}

export default App