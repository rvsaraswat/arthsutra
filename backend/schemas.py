from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


# ─── Accounting Enums (for schema validation) ─────────────────────────────

class TransactionTypeEnum(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"

class TransactionNatureEnum(str, Enum):
    SALARY = "salary"
    BUSINESS_INCOME = "business_income"
    INVESTMENT_INCOME = "investment_income"
    GIFT_RECEIVED = "gift_received"
    REFUND = "refund"
    OTHER_INCOME = "other_income"
    PURCHASE = "purchase"
    SUBSCRIPTION = "subscription"
    BILL_PAYMENT = "bill_payment"
    REIMBURSEMENT_PAID = "reimbursement_paid"
    GIFT_GIVEN = "gift_given"
    OTHER_EXPENSE = "other_expense"
    INTERNAL_TRANSFER = "internal_transfer"
    CC_BILL_PAYMENT = "cc_bill_payment"
    REIMBURSEMENT_RECEIVED = "reimbursement_received"
    LOAN_GIVEN = "loan_given"
    LOAN_RECEIVED = "loan_received"
    LOAN_REPAID = "loan_repaid"
    ADJUSTMENT = "adjustment"

class AccountingTypeEnum(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    RECEIVABLE = "receivable"
    PAYABLE = "payable"

class TransactionBase(BaseModel):
    description: str
    amount: float
    currency: str = "INR"
    transaction_type: str
    transaction_nature: Optional[str] = None
    date: datetime
    account: Optional[str] = None
    reference: Optional[str] = None

    # Double-entry accounting
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    counterparty: Optional[str] = None
    
    # Ingestion Metadata
    amount_original: Optional[float] = None
    currency_original: Optional[str] = None
    exchange_rate: Optional[float] = None
    source: Optional[str] = "manual"
    source_file: Optional[str] = None
    raw_data: Optional[str] = None

    # Enriched metadata for ML / auto-categorization
    merchant_name: Optional[str] = None
    merchant_category: Optional[str] = None
    transaction_method: Optional[str] = None
    location: Optional[str] = None
    card_last_four: Optional[str] = None
    metadata_json: Optional[str] = None

    tags: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: bool = False
    is_duplicate: bool = False
    confidence_score: Optional[float] = None

class TransactionCreate(TransactionBase):
    user_id: int
    category_id: Optional[int] = None
    account_id: Optional[int] = None

class TransactionOut(TransactionBase):
    id: int
    user_id: int
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionUpdate(BaseModel):
    """Schema for editing a transaction. All fields optional."""
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    transaction_type: Optional[str] = None
    transaction_nature: Optional[str] = None
    date: Optional[datetime] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    account: Optional[str] = None
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    counterparty: Optional[str] = None
    merchant_name: Optional[str] = None
    merchant_category: Optional[str] = None
    transaction_method: Optional[str] = None
    location: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: Optional[bool] = None


class TransactionAuditOut(BaseModel):
    id: int
    transaction_id: int
    user_id: int
    action: str
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str
    type: str
    icon: Optional[str] = None
    color: Optional[str] = None
    is_custom: bool = False
    confidence_threshold: float = 0.7

class CategoryCreate(CategoryBase):
    user_id: int

class CategoryOut(CategoryBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class BudgetBase(BaseModel):
    name: str
    amount: float
    period: str
    start_date: datetime
    end_date: datetime
    is_active: bool = True

class BudgetCreate(BudgetBase):
    user_id: int
    category_id: Optional[int] = None

class BudgetOut(BudgetBase):
    id: int
    user_id: int
    category_id: Optional[int] = None

    class Config:
        from_attributes = True

class GoalBase(BaseModel):
    name: str
    description: Optional[str] = None
    target_amount: float
    current_amount: float = 0.0
    target_date: datetime
    category: Optional[str] = None
    is_active: bool = True

class GoalCreate(GoalBase):
    user_id: int

class GoalOut(GoalBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class AssetBase(BaseModel):
    name: str
    type: str
    quantity: float
    unit: Optional[str] = None
    purchase_price: float
    current_value: float
    currency: str = "INR"
    purchase_date: datetime
    notes: Optional[str] = None

class AssetCreate(AssetBase):
    user_id: int

class AssetOut(AssetBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class AnalyticsSummary(BaseModel):
    total_income: float
    total_expenses: float
    net_cashflow: float
    savings_rate: float

class ForecastResponse(BaseModel):
    horizon_days: int
    forecast: List[float]

class ChatRequest(BaseModel):
    user_id: int
    message: str

class ChatResponse(BaseModel):
    reply: str


# ─── Account schemas ───

class AccountBase(BaseModel):
    name: str
    account_type: str  # savings, current, NRO, NRE, FD, PPF, stocks, receivable, payable, etc.
    institution: Optional[str] = None
    account_number_masked: Optional[str] = None
    currency: str = "INR"
    balance: float = 0.0
    is_active: bool = True
    icon: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None
    accounting_type: Optional[str] = None  # asset, liability, receivable, payable
    counterparty: Optional[str] = None  # For receivable/payable accounts

class AccountCreate(AccountBase):
    user_id: int

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    account_type: Optional[str] = None
    institution: Optional[str] = None
    account_number_masked: Optional[str] = None
    currency: Optional[str] = None
    balance: Optional[float] = None
    is_active: Optional[bool] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None
    accounting_type: Optional[str] = None
    counterparty: Optional[str] = None

class AccountOut(AccountBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Accounting / Ledger schemas ───

class LedgerEntryOut(BaseModel):
    id: int
    transaction_id: int
    account_id: Optional[int] = None
    debit: float
    credit: float
    entry_date: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AccountingTransactionCreate(BaseModel):
    """Full accounting-aware transaction creation."""
    user_id: int
    description: str
    amount: float
    currency: str = "INR"
    date: datetime
    transaction_type: TransactionTypeEnum
    transaction_nature: TransactionNatureEnum
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    counterparty: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    reference: Optional[str] = None


class ValidationRequest(BaseModel):
    """For pre-submit validation from frontend."""
    transaction_type: str
    transaction_nature: str
    amount: float
    currency: str = "INR"
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    from_account_type: Optional[str] = None
    to_account_type: Optional[str] = None
    category: Optional[str] = None
    counterparty: Optional[str] = None


class ValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = []


class ClassificationRequest(BaseModel):
    description: str
    amount: float = 0.0
    from_account_type: Optional[str] = None
    to_account_type: Optional[str] = None


class ClassificationResponse(BaseModel):
    transaction_type: str
    transaction_nature: str
    confidence: float
    reasoning: str = ""


class UXHintsResponse(BaseModel):
    show_category: bool
    require_counterparty: bool
    require_both_accounts: bool
    affects_net_worth: bool


class BalanceSheetResponse(BaseModel):
    as_of: str
    assets: List[dict]
    liabilities: List[dict]
    receivables: List[dict]
    payables: List[dict]
    total_assets: float
    total_liabilities: float
    net_worth: float


class OutstandingLoansResponse(BaseModel):
    loans_given: List[dict]
    loans_received: List[dict]
    total_receivable: float
    total_payable: float
    net_loan_position: float
