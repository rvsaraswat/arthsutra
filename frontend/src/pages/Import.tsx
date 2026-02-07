import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Upload, FileText, Check, AlertCircle, Trash2, Lock, Loader2,
  Building2, CreditCard, Sparkles, Info, X
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useCurrency } from '../contexts/CurrencyContext';

interface AccountOption {
  id: number;
  name: string;
  account_type: string;
  institution: string | null;
}

interface DetectionInfo {
  bank_name: string | null;
  bank_code: string | null;
  account_type: string | null;
  account_type_label: string | null;
  confidence: number;
  detection_source: string | null;
  transaction_count: number;
}

const ACCOUNT_TYPES = [
  { value: 'savings', label: 'Savings Account' },
  { value: 'current', label: 'Current Account' },
  { value: 'salary', label: 'Salary Account' },
  { value: 'NRO', label: 'NRO Account' },
  { value: 'NRE', label: 'NRE Account' },
  { value: 'overdraft', label: 'Overdraft Account' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'FD', label: 'Fixed Deposit' },
  { value: 'RD', label: 'Recurring Deposit' },
  { value: 'PPF', label: 'PPF Account' },
  { value: 'EPF', label: 'EPF Account' },
  { value: 'NPS', label: 'NPS Account' },
  { value: 'stocks', label: 'Stocks / Demat' },
  { value: 'mutual_funds', label: 'Mutual Funds' },
  { value: 'bonds', label: 'Bonds' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'wallet', label: 'Digital Wallet' },
  { value: 'cash', label: 'Cash' },
  { value: 'other', label: 'Other' },
];

const Import = () => {
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState('');
  const [preview, setPreview] = useState<any[]>([]);
  const [detection, setDetection] = useState<DetectionInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<AccountOption[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  const [overrideBank, setOverrideBank] = useState('');
  const [overrideAccountType, setOverrideAccountType] = useState('');
  const [showDetectionPanel, setShowDetectionPanel] = useState(true);
  const navigate = useNavigate();
  const { currency, formatAmount } = useCurrency();

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const res = await axios.get('/api/v1/accounts?user_id=1');
      setAccounts(res.data.accounts || []);
    } catch {
      // Accounts not mandatory
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setPreview([]);
      setDetection(null);
      setOverrideBank('');
      setOverrideAccountType('');
      setSelectedAccountId('');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setLoadingMessage('Analyzing file...');
    setError(null);
    setDetection(null);
    const formData = new FormData();
    formData.append('file', file);
    if (password) {
      formData.append('password', password);
    }
    formData.append('target_currency', currency);

    try {
      setLoadingMessage('Extracting transactions & detecting bank...');
      const response = await axios.post('/api/v1/ingestion/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const data = response.data;
      const txns = data.transactions || data;
      const det = data.detection || null;

      setPreview(Array.isArray(txns) ? txns : []);
      setDetection(det);

      if (det?.bank_name) setOverrideBank(det.bank_name);
      if (det?.account_type) setOverrideAccountType(det.account_type);
      setShowDetectionPanel(true);

      if ((Array.isArray(txns) ? txns : []).length === 0) {
        setError('No transactions could be extracted from this file.');
      }
    } catch (err: any) {
      let msg: string;
      if (err.response?.data?.detail) {
        msg = err.response.data.detail;
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        msg = 'Cannot connect to backend server. Please ensure the backend is running on port 8000.';
      } else {
        msg = err.message || 'Failed to parse file. Please check the file format and try again.';
      }
      console.error('Upload error:', err);
      setError(msg);
    } finally {
      setLoading(false);
      setLoadingMessage('');
    }
  };

  const handleConfirm = async () => {
    if (preview.length === 0) return;
    setConfirming(true);
    setLoadingMessage('Saving to database...');

    const txns = preview.map((txn: any) => ({
      ...txn,
      account_id: selectedAccountId ? parseInt(selectedAccountId) : undefined,
    }));

    const params = new URLSearchParams();
    const bankName = overrideBank || detection?.bank_name || '';
    const accountType = overrideAccountType || detection?.account_type || '';
    if (bankName) params.set('bank_name', bankName);
    if (accountType) params.set('account_type', accountType);

    try {
      await axios.post(
        `/api/v1/ingestion/confirm?${params.toString()}`,
        txns
      );
      navigate('/transactions');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save transactions');
    } finally {
      setConfirming(false);
      setLoadingMessage('');
    }
  };

  const removeRow = (index: number) => {
    const updated = [...preview];
    updated.splice(index, 1);
    setPreview(updated);
  };

  const confidenceColor = (conf: number) => {
    if (conf >= 0.7) return 'text-green-400';
    if (conf >= 0.4) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const confidenceLabel = (conf: number) => {
    if (conf >= 0.7) return 'High';
    if (conf >= 0.4) return 'Medium';
    return 'Low';
  };

  const reset = () => {
    setFile(null);
    setPreview([]);
    setDetection(null);
    setError(null);
    setPassword('');
    setOverrideBank('');
    setOverrideAccountType('');
    setSelectedAccountId('');
  };

  return (
    <div className="space-y-6 animate-fade-in p-6">
      <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
        Import Statement
      </h1>

      {/* Upload Box */}
      <div className={`card ${error ? '!border-red-500/50' : ''} text-center`}>
        <input
          type="file"
          id="file-upload"
          className="hidden"
          accept=".pdf,.csv,.xlsx,.xls,.txt"
          onChange={handleFileChange}
        />
        {!file ? (
          <label
            htmlFor="file-upload"
            className="cursor-pointer flex flex-col items-center justify-center space-y-4 hover:opacity-80 transition py-8"
          >
            <div className="p-5 bg-violet-500/20 rounded-2xl text-violet-400">
              <Upload size={36} />
            </div>
            <div>
              <p className="text-lg font-semibold text-white">
                Drop or click to upload bank statement
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Supports PDF, CSV, Excel — auto-detects bank &amp; account type
              </p>
            </div>
          </label>
        ) : (
          <div className="space-y-5 py-4">
            <div className="flex items-center justify-center gap-3">
              <div className="flex items-center gap-2 text-green-400 bg-green-900/20 py-2.5 px-5 rounded-xl">
                <FileText size={18} />
                <span className="font-medium text-sm">{file.name}</span>
                <button onClick={reset} className="ml-1 hover:text-white transition">
                  <X size={15} />
                </button>
              </div>
            </div>

            <div className="flex items-center justify-center gap-3 max-w-xl mx-auto flex-wrap">
              <div className="relative flex-1 min-w-[200px]">
                <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  type="password"
                  placeholder="Password (if encrypted)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 transition"
                />
              </div>
            </div>

            <button
              onClick={handleUpload}
              disabled={loading}
              className="btn-primary mx-auto flex items-center gap-2 px-8 py-3"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  <span>Analyze &amp; Detect</span>
                </>
              )}
            </button>
            {loadingMessage && (
              <p className="text-sm text-violet-300 mt-1 animate-pulse text-center">
                {loadingMessage}
              </p>
            )}
          </div>
        )}

        {error && (
          <div className="mt-5 text-red-300 bg-red-900/20 border border-red-500/20 p-4 rounded-xl flex items-center justify-center gap-3">
            <AlertCircle size={18} className="shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        )}
      </div>

      {/* Detection Result Panel */}
      {detection && showDetectionPanel && (
        <div className="card !border-violet-500/30 !bg-violet-500/5">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-violet-500/20 rounded-lg">
                <Sparkles size={20} className="text-violet-400" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">
                  Auto-Detected Bank &amp; Account
                </h3>
                <p className="text-xs text-gray-400">
                  Confidence:{' '}
                  <span className={confidenceColor(detection.confidence)}>
                    {confidenceLabel(detection.confidence)} ({Math.round(detection.confidence * 100)}%)
                  </span>
                  {detection.detection_source && (
                    <span className="ml-2 text-gray-500">
                      via {detection.detection_source.replace('_', ' ')}
                    </span>
                  )}
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowDetectionPanel(false)}
              className="text-gray-500 hover:text-white transition"
            >
              <X size={16} />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Bank Name */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                <Building2 size={12} className="inline mr-1" />
                Bank / Institution
              </label>
              <input
                type="text"
                value={overrideBank}
                onChange={(e) => setOverrideBank(e.target.value)}
                placeholder="Enter bank name"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 transition"
              />
              {detection.bank_name && overrideBank !== detection.bank_name && (
                <button
                  onClick={() => setOverrideBank(detection.bank_name!)}
                  className="text-xs text-violet-400 hover:text-violet-300 mt-1"
                >
                  Reset to detected: {detection.bank_name}
                </button>
              )}
            </div>

            {/* Account Type */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                <CreditCard size={12} className="inline mr-1" />
                Account Type
              </label>
              <select
                value={overrideAccountType}
                onChange={(e) => setOverrideAccountType(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-violet-500/50 transition appearance-none"
              >
                <option value="">Select account type</option>
                {ACCOUNT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              {detection.account_type && overrideAccountType !== detection.account_type && (
                <button
                  onClick={() => setOverrideAccountType(detection.account_type!)}
                  className="text-xs text-violet-400 hover:text-violet-300 mt-1"
                >
                  Reset to detected: {detection.account_type_label}
                </button>
              )}
            </div>
          </div>

          {/* Existing account override */}
          {accounts.length > 0 && (
            <div className="mt-4 pt-4 border-t border-white/5">
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                Or link to an existing account (overrides above)
              </label>
              <select
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-violet-500/50 transition appearance-none"
              >
                <option value="">Auto-create from detected bank</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} — {a.account_type}
                    {a.institution ? ` (${a.institution})` : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="mt-3 flex items-start gap-2 text-xs text-gray-500">
            <Info size={14} className="shrink-0 mt-0.5" />
            <span>
              {selectedAccountId
                ? 'Transactions will be linked to the selected account.'
                : overrideBank
                  ? `A new "${overrideBank} ${ACCOUNT_TYPES.find(t => t.value === overrideAccountType)?.label || overrideAccountType}" account will be auto-created if it doesn't exist.`
                  : 'Select or confirm bank details to link transactions to an account.'}
            </span>
          </div>
        </div>
      )}

      {/* Preview Table */}
      {preview.length > 0 && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold text-white">
                Preview — {preview.length} transactions
              </h2>
              {(overrideBank || detection?.bank_name) && (
                <p className="text-sm text-gray-400 mt-1">
                  From{' '}
                  <span className="text-violet-400 font-medium">
                    {overrideBank || detection?.bank_name}
                  </span>
                  {(overrideAccountType || detection?.account_type) && (
                    <>
                      {' · '}
                      <span className="text-blue-400">
                        {ACCOUNT_TYPES.find(
                          (t) =>
                            t.value ===
                            (overrideAccountType || detection?.account_type)
                        )?.label ||
                          overrideAccountType ||
                          detection?.account_type}
                      </span>
                    </>
                  )}
                </p>
              )}
            </div>
            <button
              onClick={handleConfirm}
              disabled={confirming}
              className="btn-primary flex items-center gap-2 px-6 py-2.5"
            >
              {confirming ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Check size={16} />
                  <span>Confirm Import</span>
                </>
              )}
            </button>
          </div>

          <div className="overflow-x-auto card !p-0">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-gray-400 border-b border-white/10 text-xs uppercase tracking-wider">
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3">Merchant</th>
                  <th className="px-4 py-3">Method</th>
                  <th className="px-4 py-3 text-right">Amount</th>
                  <th className="px-4 py-3 text-right">Original</th>
                  <th className="px-4 py-3">Cur</th>
                  <th className="px-4 py-3 w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {preview.map((txn, idx) => (
                  <tr key={idx} className="hover:bg-white/5 transition group">
                    <td className="px-4 py-3 text-gray-300 text-sm whitespace-nowrap">
                      {new Date(txn.date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-white font-medium text-sm max-w-[220px] truncate">
                      {txn.description}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {txn.merchant_name || '—'}
                    </td>
                    <td className="px-4 py-3">
                      {txn.transaction_method ? (
                        <span className="text-xs bg-white/5 border border-white/10 rounded-md px-2 py-0.5 text-gray-300">
                          {txn.transaction_method}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td
                      className={`px-4 py-3 text-right font-bold text-sm ${
                        txn.amount > 0 ? 'text-green-400' : 'text-red-400'
                      }`}
                    >
                      {formatAmount(Math.abs(txn.amount))}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-500 text-sm">
                      {txn.amount_original ? txn.amount_original.toFixed(2) : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {txn.currency_original || txn.currency || 'INR'}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => removeRow(idx)}
                        className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition"
                      >
                        <Trash2 size={15} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Bottom action bar */}
          <div className="flex items-center justify-between bg-white/5 rounded-xl px-5 py-3 border border-white/10">
            <span className="text-sm text-gray-400">
              {preview.length} transactions ready to import
            </span>
            <div className="flex items-center gap-3">
              <button
                onClick={reset}
                className="text-sm text-gray-400 hover:text-white transition px-4 py-2"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={confirming}
                className="btn-primary flex items-center gap-2 px-6 py-2"
              >
                {confirming ? (
                  <Loader2 size={15} className="animate-spin" />
                ) : (
                  <Check size={15} />
                )}
                <span>Confirm Import</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Import;
