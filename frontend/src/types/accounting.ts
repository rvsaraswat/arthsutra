/**
 * Arthsutra Accounting Domain Types
 * ==================================
 * TypeScript mirrors of the backend accounting engine.
 * Single source of truth for the frontend.
 */

// ─── Transaction Type (top-level) ────────────────────────────────────────

export enum TransactionType {
  INCOME = "income",
  EXPENSE = "expense",
  TRANSFER = "transfer",
}

// ─── Transaction Nature (semantic intent) ────────────────────────────────

export enum TransactionNature {
  // Income
  SALARY = "salary",
  BUSINESS_INCOME = "business_income",
  INVESTMENT_INCOME = "investment_income",
  GIFT_RECEIVED = "gift_received",
  REFUND = "refund",
  OTHER_INCOME = "other_income",

  // Expense
  PURCHASE = "purchase",
  SUBSCRIPTION = "subscription",
  BILL_PAYMENT = "bill_payment",
  REIMBURSEMENT_PAID = "reimbursement_paid",
  GIFT_GIVEN = "gift_given",
  OTHER_EXPENSE = "other_expense",

  // Transfer (no net-worth impact)
  INTERNAL_TRANSFER = "internal_transfer",
  CC_BILL_PAYMENT = "cc_bill_payment",
  REIMBURSEMENT_RECEIVED = "reimbursement_received",

  // Loans (no net-worth impact at origination)
  LOAN_GIVEN = "loan_given",
  LOAN_RECEIVED = "loan_received",
  LOAN_REPAID = "loan_repaid",

  // Catch-all
  ADJUSTMENT = "adjustment",
}

// ─── Account types ───────────────────────────────────────────────────────

export enum AccountingType {
  ASSET = "asset",
  LIABILITY = "liability",
  RECEIVABLE = "receivable",
  PAYABLE = "payable",
}

// ─── Valid natures per type ──────────────────────────────────────────────

export const VALID_NATURES: Record<TransactionType, TransactionNature[]> = {
  [TransactionType.INCOME]: [
    TransactionNature.SALARY,
    TransactionNature.BUSINESS_INCOME,
    TransactionNature.INVESTMENT_INCOME,
    TransactionNature.GIFT_RECEIVED,
    TransactionNature.REFUND,
    TransactionNature.OTHER_INCOME,
  ],
  [TransactionType.EXPENSE]: [
    TransactionNature.PURCHASE,
    TransactionNature.SUBSCRIPTION,
    TransactionNature.BILL_PAYMENT,
    TransactionNature.REIMBURSEMENT_PAID,
    TransactionNature.GIFT_GIVEN,
    TransactionNature.OTHER_EXPENSE,
  ],
  [TransactionType.TRANSFER]: [
    TransactionNature.INTERNAL_TRANSFER,
    TransactionNature.CC_BILL_PAYMENT,
    TransactionNature.REIMBURSEMENT_RECEIVED,
    TransactionNature.LOAN_GIVEN,
    TransactionNature.LOAN_RECEIVED,
    TransactionNature.LOAN_REPAID,
    TransactionNature.ADJUSTMENT,
  ],
};

// ─── Account ─────────────────────────────────────────────────────────────

export interface Account {
  id: number;
  name: string;
  account_type: string;
  accounting_type: AccountingType;
  institution?: string;
  account_number_masked?: string;
  currency: string;
  balance: number;
  is_active: boolean;
  counterparty?: string;
  icon?: string;
  color?: string;
  notes?: string;
}

// ─── Transaction ─────────────────────────────────────────────────────────

export interface Transaction {
  id: number;
  date: string;
  amount: number;
  currency: string;

  transaction_type: TransactionType;
  transaction_nature?: TransactionNature;

  from_account_id?: number;
  to_account_id?: number;
  account_id?: number;

  category?: string;
  category_id?: number;
  counterparty?: string;
  description: string;
  notes?: string;
  tags?: string;
  reference?: string;

  // Enrichment
  merchant_name?: string;
  merchant_category?: string;
  transaction_method?: string;

  // Metadata
  source?: string;
  confidence_score?: number;
  is_recurring?: boolean;
  created_at?: string;
  updated_at?: string;
}

// ─── Ledger Entry ────────────────────────────────────────────────────────

export interface LedgerEntry {
  id: number;
  transaction_id: number;
  account_id: number | null;
  debit: number;
  credit: number;
  entry_date: string;
  description?: string;
}

// ─── Create / Update DTOs ────────────────────────────────────────────────

export interface AccountingTransactionCreate {
  user_id: number;
  description: string;
  amount: number;
  currency: string;
  date: string;
  transaction_type: TransactionType;
  transaction_nature: TransactionNature;
  from_account_id?: number;
  to_account_id?: number;
  category?: string;
  category_id?: number;
  counterparty?: string;
  notes?: string;
  tags?: string;
  reference?: string;
}

// ─── Validation ──────────────────────────────────────────────────────────

export interface ValidationRequest {
  transaction_type: string;
  transaction_nature: string;
  amount: number;
  currency?: string;
  from_account_id?: number;
  to_account_id?: number;
  from_account_type?: string;
  to_account_type?: string;
  category?: string;
  counterparty?: string;
}

export interface ValidationResponse {
  valid: boolean;
  errors: string[];
}

// ─── AI Classification ──────────────────────────────────────────────────

export interface ClassificationResult {
  transaction_type: TransactionType;
  transaction_nature: TransactionNature;
  confidence: number;
  reasoning: string;
}

// ─── UX Hints ────────────────────────────────────────────────────────────

export interface UXHints {
  show_category: boolean;
  require_counterparty: boolean;
  require_both_accounts: boolean;
  affects_net_worth: boolean;
}

// ─── Reports ─────────────────────────────────────────────────────────────

export interface CashFlowReport {
  period: { start: string; end: string };
  inflows: number;
  outflows: number;
  net_cash_flow: number;
  by_month: Array<{
    month: string;
    inflows: number;
    outflows: number;
    net: number;
  }>;
  by_type: {
    income: number;
    expense: number;
    transfer_in: number;
    transfer_out: number;
  };
}

export interface IncomeExpenseSummary {
  total_income: number;
  total_expenses: number;
  net: number;
  savings_rate: number;
  income_breakdown: Array<{ nature: string; total: number }>;
  expense_breakdown: Array<{ nature: string; total: number }>;
}

export interface BalanceSheet {
  as_of: string;
  assets: Array<BalanceSheetItem>;
  liabilities: Array<BalanceSheetItem>;
  receivables: Array<BalanceSheetItem>;
  payables: Array<BalanceSheetItem>;
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
}

export interface BalanceSheetItem {
  account_id: number;
  name: string;
  account_type: string;
  accounting_type: string;
  balance: number;
  currency: string;
}

export interface OutstandingLoans {
  loans_given: Array<{
    account_id: number;
    counterparty: string;
    balance: number;
    currency: string;
  }>;
  loans_received: Array<{
    account_id: number;
    counterparty: string;
    balance: number;
    currency: string;
  }>;
  total_receivable: number;
  total_payable: number;
  net_loan_position: number;
}

export interface NetWorthTimeline {
  timeline: Array<{
    month: string;
    net_worth: number;
    income: number;
    expenses: number;
  }>;
}

// ─── Nature display helpers ──────────────────────────────────────────────

export const NATURE_LABELS: Record<TransactionNature, string> = {
  [TransactionNature.SALARY]: "Salary",
  [TransactionNature.BUSINESS_INCOME]: "Business Income",
  [TransactionNature.INVESTMENT_INCOME]: "Investment Income",
  [TransactionNature.GIFT_RECEIVED]: "Gift Received",
  [TransactionNature.REFUND]: "Refund",
  [TransactionNature.OTHER_INCOME]: "Other Income",
  [TransactionNature.PURCHASE]: "Purchase",
  [TransactionNature.SUBSCRIPTION]: "Subscription",
  [TransactionNature.BILL_PAYMENT]: "Bill Payment",
  [TransactionNature.REIMBURSEMENT_PAID]: "Reimbursement Paid",
  [TransactionNature.GIFT_GIVEN]: "Gift Given",
  [TransactionNature.OTHER_EXPENSE]: "Other Expense",
  [TransactionNature.INTERNAL_TRANSFER]: "Internal Transfer",
  [TransactionNature.CC_BILL_PAYMENT]: "CC Bill Payment",
  [TransactionNature.REIMBURSEMENT_RECEIVED]: "Reimbursement Received",
  [TransactionNature.LOAN_GIVEN]: "Loan Given",
  [TransactionNature.LOAN_RECEIVED]: "Loan Received",
  [TransactionNature.LOAN_REPAID]: "Loan Repaid",
  [TransactionNature.ADJUSTMENT]: "Adjustment",
};

/**
 * Returns true if a transfer nature does NOT change net worth.
 */
export function isNetWorthNeutral(nature: TransactionNature): boolean {
  const neutralNatures = new Set<TransactionNature>([
    TransactionNature.INTERNAL_TRANSFER,
    TransactionNature.CC_BILL_PAYMENT,
    TransactionNature.LOAN_GIVEN,
    TransactionNature.LOAN_RECEIVED,
    TransactionNature.LOAN_REPAID,
    TransactionNature.REIMBURSEMENT_RECEIVED,
    TransactionNature.ADJUSTMENT,
  ]);
  return neutralNatures.has(nature);
}
