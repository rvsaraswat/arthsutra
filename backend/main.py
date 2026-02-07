"""
Main FastAPI application for Arthsutra - AI Personal Finance Manager.
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Optional

from config import settings
from models import create_tables, get_session
from models import User, Transaction, Category, Budget, Goal, Asset, AuditLog, FinancialSnapshot
from schemas import (
    TransactionCreate,
    TransactionOut,
    CategoryCreate,
    CategoryOut,
    BudgetCreate,
    BudgetOut,
    GoalCreate,
    GoalOut,
    AssetCreate,
    AssetOut,
    AnalyticsSummary,
    ForecastResponse,
    ChatRequest,
    ChatResponse,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()


# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    create_tables()
    logger.info("Database tables created")
    yield
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-driven Personal Finance Manager running locally",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


# API v1 router
@app.get(f"{settings.API_V1_PREFIX}/status")
async def api_status():
    """API status endpoint."""
    return {
        "status": "operational",
        "version": settings.APP_VERSION,
        "database": "connected",
        "ai_model": settings.OLLAMA_MODEL
    }


# Authentication endpoints (placeholder)
@app.post(f"{settings.API_V1_PREFIX}/auth/register")
async def register_user():
    """Register a new user."""
    # TODO: Implement user registration
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User registration not yet implemented"
    )


@app.post(f"{settings.API_V1_PREFIX}/auth/login")
async def login_user():
    """User login."""
    # TODO: Implement user login
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User login not yet implemented"
    )


# Transaction endpoints
@app.get(f"{settings.API_V1_PREFIX}/transactions")
async def get_transactions(
    user_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session=Depends(get_session)
):
    """Get transactions with optional filters."""
    query = session.query(Transaction).filter(Transaction.user_id == user_id)

    if start_date:
        query = query.filter(Transaction.date >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Transaction.date <= datetime.fromisoformat(end_date))
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    transactions = query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()

    return {
        "transactions": [
            {
                "id": t.id,
                "description": t.description,
                "amount": t.amount,
                "currency": t.currency,
                "type": t.transaction_type,
                "date": t.date.isoformat(),
                "account": t.account,
                "reference": t.reference,
                "tags": t.tags,
                "notes": t.notes,
                "is_recurring": t.is_recurring,
                "is_duplicate": t.is_duplicate,
                "confidence_score": t.confidence_score
            }
            for t in transactions
        ],
        "total": len(transactions)
    }


@app.post(f"{settings.API_V1_PREFIX}/transactions")
async def add_transaction(transaction_data: TransactionCreate, session=Depends(get_session)):
    """Add a new transaction."""
    tx = Transaction(
        user_id=transaction_data.user_id,
        category_id=transaction_data.category_id,
        description=transaction_data.description,
        amount=transaction_data.amount,
        currency=transaction_data.currency,
        transaction_type=transaction_data.transaction_type,
        date=transaction_data.date,
        account=transaction_data.account,
        reference=transaction_data.reference,
        tags=transaction_data.tags,
        notes=transaction_data.notes,
        is_recurring=transaction_data.is_recurring,
        is_duplicate=transaction_data.is_duplicate,
        confidence_score=transaction_data.confidence_score,
    )
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return TransactionOut.from_orm(tx)


# Category endpoints
@app.get(f"{settings.API_V1_PREFIX}/categories")
async def get_categories(user_id: int, session=Depends(get_session)):
    """Get all categories for a user."""
    categories = session.query(Category).filter(Category.user_id == user_id).all()

    return {
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type,
                "icon": c.icon,
                "color": c.color,
                "is_custom": c.is_custom,
                "confidence_threshold": c.confidence_threshold
            }
            for c in categories
        ]
    }


@app.post(f"{settings.API_V1_PREFIX}/categories")
async def add_category(category_data: CategoryCreate, session=Depends(get_session)):
    """Add a new category."""
    cat = Category(
        user_id=category_data.user_id,
        name=category_data.name,
        type=category_data.type,
        icon=category_data.icon,
        color=category_data.color,
        is_custom=category_data.is_custom,
        confidence_threshold=category_data.confidence_threshold,
    )
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return CategoryOut.from_orm(cat)


# Budget endpoints
@app.get(f"{settings.API_V1_PREFIX}/budgets")
async def get_budgets(user_id: int, session=Depends(get_session)):
    """Get all budgets for a user."""
    budgets = session.query(Budget).filter(Budget.user_id == user_id).all()

    return {
        "budgets": [
            {
                "id": b.id,
                "name": b.name,
                "amount": b.amount,
                "period": b.period,
                "start_date": b.start_date.isoformat(),
                "end_date": b.end_date.isoformat(),
                "is_active": b.is_active
            }
            for b in budgets
        ]
    }


@app.post(f"{settings.API_V1_PREFIX}/budgets")
async def add_budget(budget_data: BudgetCreate, session=Depends(get_session)):
    """Add a new budget."""
    bud = Budget(
        user_id=budget_data.user_id,
        category_id=budget_data.category_id,
        name=budget_data.name,
        amount=budget_data.amount,
        period=budget_data.period,
        start_date=budget_data.start_date,
        end_date=budget_data.end_date,
        is_active=budget_data.is_active,
    )
    session.add(bud)
    session.commit()
    session.refresh(bud)
    return BudgetOut.from_orm(bud)


# Goal endpoints
@app.get(f"{settings.API_V1_PREFIX}/goals")
async def get_goals(user_id: int, session=Depends(get_session)):
    """Get all goals for a user."""
    goals = session.query(Goal).filter(Goal.user_id == user_id).all()

    return {
        "goals": [
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "target_amount": g.target_amount,
                "current_amount": g.current_amount,
                "target_date": g.target_date.isoformat(),
                "category": g.category,
                "is_active": g.is_active
            }
            for g in goals
        ]
    }


@app.post(f"{settings.API_V1_PREFIX}/goals")
async def add_goal(goal_data: GoalCreate, session=Depends(get_session)):
    """Add a new goal."""
    goal = Goal(
        user_id=goal_data.user_id,
        name=goal_data.name,
        description=goal_data.description,
        target_amount=goal_data.target_amount,
        current_amount=goal_data.current_amount,
        target_date=goal_data.target_date,
        category=goal_data.category,
        is_active=goal_data.is_active,
    )
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return GoalOut.from_orm(goal)


# Asset endpoints
@app.get(f"{settings.API_V1_PREFIX}/assets")
async def get_assets(user_id: int, session=Depends(get_session)):
    """Get all assets for a user."""
    assets = session.query(Asset).filter(Asset.user_id == user_id).all()

    return {
        "assets": [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type,
                "quantity": a.quantity,
                "unit": a.unit,
                "purchase_price": a.purchase_price,
                "current_value": a.current_value,
                "currency": a.currency,
                "purchase_date": a.purchase_date.isoformat(),
                "notes": a.notes
            }
            for a in assets
        ]
    }


@app.post(f"{settings.API_V1_PREFIX}/assets")
async def add_asset(asset_data: AssetCreate, session=Depends(get_session)):
    """Add a new asset."""
    asset = Asset(
        user_id=asset_data.user_id,
        name=asset_data.name,
        type=asset_data.type,
        quantity=asset_data.quantity,
        unit=asset_data.unit,
        purchase_price=asset_data.purchase_price,
        current_value=asset_data.current_value,
        currency=asset_data.currency,
        purchase_date=asset_data.purchase_date,
        notes=asset_data.notes,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return AssetOut.from_orm(asset)


# Analytics endpoints
@app.get(f"{settings.API_V1_PREFIX}/analytics/cashflow")
async def get_cashflow(
    user_id: int,
    start_date: str,
    end_date: str,
    session=Depends(get_session)
):
    """Get cash-flow analysis for a period."""
    # TODO: Implement cash-flow calculation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Cash-flow analysis not yet implemented"
    )


@app.get(f"{settings.API_V1_PREFIX}/analytics/networth")
async def get_networth(
    user_id: int,
    date: Optional[str] = None,
    session=Depends(get_session)
):
    """Get net-worth calculation."""
    # TODO: Implement net-worth calculation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Net-worth calculation not yet implemented"
    )


@app.get(f"{settings.API_V1_PREFIX}/analytics/budget")
async def get_budget_analysis(
    user_id: int,
    period: str = "monthly",
    session=Depends(get_session)
):
    """Get budget utilization analysis."""
    # TODO: Implement budget analysis
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Budget analysis not yet implemented"
    )


@app.get(f"{settings.API_V1_PREFIX}/analytics/summary")
async def get_analytics_summary(user_id: int, session=Depends(get_session)):
    """Get analytics summary for a user."""
    txs = session.query(Transaction).filter(Transaction.user_id == user_id).all()
    total_income = sum(t.amount for t in txs if t.transaction_type == 'income')
    total_expenses = sum(t.amount for t in txs if t.transaction_type == 'expense')
    net_cashflow = total_income - total_expenses
    savings_rate = (net_cashflow / total_income) * 100 if total_income else 0
    return AnalyticsSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net_cashflow=net_cashflow,
        savings_rate=savings_rate,
    )


# Forecasting endpoints
@app.get(f"{settings.API_V1_PREFIX}/forecasting/expenses")
async def forecast_expenses(
    user_id: int,
    horizon_days: int = 30,
    session=Depends(get_session)
):
    """Get expense forecasting."""
    # TODO: Implement expense forecasting
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Expense forecasting not yet implemented"
    )


@app.get(f"{settings.API_V1_PREFIX}/forecasting/savings")
async def forecast_savings(
    user_id: int,
    horizon_days: int = 30,
    session=Depends(get_session)
):
    """Get savings trajectory forecasting."""
    # TODO: Implement savings forecasting
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Savings forecasting not yet implemented"
    )


@app.get(f"{settings.API_V1_PREFIX}/forecasting/retirement")
async def retirement_simulator(
    user_id: int,
    current_age: int,
    retirement_age: int,
    monthly_contribution: float,
    expected_return: float = 0.08,
    inflation_rate: float = 0.06,
    session=Depends(get_session)
):
    """Run retirement corpus simulator."""
    # TODO: Implement retirement simulator
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Retirement simulator not yet implemented"
    )


# AI / Chat endpoints
@app.post(f"{settings.API_V1_PREFIX}/ai/chat")
async def chat_with_ai(
    chat_req: ChatRequest,
    session=Depends(get_session),
):
    """Chat with AI for financial insights."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": chat_req.message,
        "stream": False,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM service error: {resp.text}",
        )
    data = resp.json()
    reply = data.get("message", {}).get("content", "")
    return ChatResponse(reply=reply)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )