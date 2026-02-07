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
    tags: Optional[str] = None
    notes: Optional[str] = None
    is_recurring: bool = False
    is_duplicate: bool = False
    confidence_score: Optional[float] = None

class TransactionCreate(TransactionBase):
    user_id: int
    category_id: Optional[int] = None

class TransactionOut(TransactionBase):
    id: int
    user_id: int
    category_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

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
