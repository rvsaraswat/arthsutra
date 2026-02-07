from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class TransactionBase(BaseModel):
    description: str
    amount: float
    currency: str = "INR"
    transaction_type: str
    date: datetime
    account: Optional[str] = None
    reference: Optional[str] = None
    
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
    date: Optional[datetime] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    account: Optional[str] = None
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
    account_type: str  # savings, current, NRO, NRE, FD, PPF, stocks, etc.
    institution: Optional[str] = None
    account_number_masked: Optional[str] = None
    currency: str = "INR"
    balance: float = 0.0
    is_active: bool = True
    icon: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None

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

class AccountOut(AccountBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
