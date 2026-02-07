"""
Main FastAPI application for Arthsutra - AI Personal Finance Manager.
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import json
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Optional

from config import settings
from ingestion.routes import router as ingestion_router
from models import create_tables, get_session
from models import User, Transaction, Category, Budget, Goal, Asset, AuditLog, FinancialSnapshot, Account, ACCOUNT_TYPES, ACCOUNT_TYPE_GROUPS, TransactionAudit
from services.currency import currency_service
from analytics.forecasting import forecast_expenses as forecast_expenses_fn
from analytics.forecasting import forecast_savings as forecast_savings_fn
from analytics.forecasting import RetirementSimulator
from analytics.cashflow import CashFlowAnalyzer
from schemas import (
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
    TransactionAuditOut,
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
    AccountCreate,
    AccountUpdate,
    AccountOut,
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

app.include_router(ingestion_router)


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
async def register_user(
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    session=Depends(get_session)
):
    """Register a new user."""
    try:
        # Check if user already exists
        existing_user = session.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists"
            )
        
        # For local-first application, we'll use simple password storage
        # In production, use proper password hashing (bcrypt, argon2, etc.)
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name or username,
            preferred_currency="INR"
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        
        logger.info(f"User registered: {username}")
        
        return {
            "user_id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "message": "User registered successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}"
        )


# ─── Currency endpoints ───

@app.get(f"{settings.API_V1_PREFIX}/currency/supported")
async def get_supported_currencies():
    """Return list of all supported currencies with symbols and names."""
    return {"currencies": currency_service.get_supported_currencies()}


@app.get(f"{settings.API_V1_PREFIX}/currency/convert")
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
):
    """Convert an amount between two currencies."""
    try:
        converted = currency_service.convert(amount, from_currency, to_currency)
        rate = currency_service.get_rate(from_currency, to_currency)
        return {
            "amount": amount,
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "converted_amount": converted,
            "rate": round(rate, 6),
            "symbol": currency_service.get_symbol(to_currency),
            "formatted": currency_service.format_amount(converted, to_currency),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── User preference endpoints ───

@app.get(f"{settings.API_V1_PREFIX}/user/preferences")
async def get_user_preferences(user_id: int = 1, session=Depends(get_session)):
    """Get user preferences including preferred currency."""
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        # Auto-create default user for local-first mode
        user = User(id=1, username="default", email="user@arthsutra.local", password_hash="local", full_name="User", preferred_currency="INR")
        session.add(user)
        session.commit()
        session.refresh(user)

    prefs = {}
    if user.preferences:
        try:
            prefs = json.loads(user.preferences)
        except Exception:
            pass

    return {
        "user_id": user.id,
        "preferred_currency": user.preferred_currency or "INR",
        "symbol": currency_service.get_symbol(user.preferred_currency or "INR"),
        "full_name": user.full_name,
        "email": user.email,
        "preferences": prefs,
    }


@app.put(f"{settings.API_V1_PREFIX}/user/preferences")
async def update_user_preferences(
    preferred_currency: Optional[str] = None,
    user_id: int = 1,
    session=Depends(get_session),
):
    """Update user preferences (currency, etc.)."""
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=1, username="default", email="user@arthsutra.local", password_hash="local", full_name="User", preferred_currency="INR")
        session.add(user)

    if preferred_currency:
        user.preferred_currency = preferred_currency.upper()

    session.commit()
    return {
        "user_id": user.id,
        "preferred_currency": user.preferred_currency,
        "symbol": currency_service.get_symbol(user.preferred_currency),
    }


@app.post(f"{settings.API_V1_PREFIX}/auth/login")
async def login_user(
    username: str,
    password: str,
    session=Depends(get_session)
):
    """User login."""
    try:
        # Find user by username or email
        user = session.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password (using simple hash for local-first app)
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if user.password_hash != password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        logger.info(f"User logged in: {username}")
        
        # For local-first application, return user info
        # In production, generate and return JWT token
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "preferred_currency": user.preferred_currency,
            "message": "Login successful"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )


# ─── Account endpoints ───

@app.get(f"{settings.API_V1_PREFIX}/accounts/types")
async def get_account_types():
    """Return all supported account types grouped by category."""
    return {
        "types": ACCOUNT_TYPES,
        "groups": ACCOUNT_TYPE_GROUPS,
    }


@app.get(f"{settings.API_V1_PREFIX}/accounts")
async def get_accounts(
    user_id: int = 1,
    account_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    session=Depends(get_session),
):
    """Get all accounts for a user, optionally filtered."""
    query = session.query(Account).filter(Account.user_id == user_id)
    if account_type:
        query = query.filter(Account.account_type == account_type)
    if is_active is not None:
        query = query.filter(Account.is_active == is_active)

    accounts = query.order_by(Account.created_at.desc()).all()

    # Compute running balance from transactions for each account
    from sqlalchemy import func as sa_func
    balance_query = (
        session.query(
            Transaction.account_id,
            sa_func.sum(Transaction.amount).label("computed_balance"),
        )
        .filter(
            Transaction.user_id == user_id,
            (Transaction.is_deleted == False) | (Transaction.is_deleted == None),
        )
        .group_by(Transaction.account_id)
        .all()
    )
    balance_map = {row.account_id: row.computed_balance or 0.0 for row in balance_query}

    return {
        "accounts": [
            {
                "id": a.id,
                "name": a.name,
                "account_type": a.account_type,
                "institution": a.institution,
                "account_number_masked": a.account_number_masked,
                "currency": a.currency,
                "balance": round(balance_map.get(a.id, 0.0), 2),
                "is_active": a.is_active,
                "icon": a.icon,
                "color": a.color,
                "notes": a.notes,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                "transaction_count": len([t for t in a.transactions if not t.is_deleted]),
            }
            for a in accounts
        ],
        "total": len(accounts),
    }


@app.post(f"{settings.API_V1_PREFIX}/accounts")
async def create_account(
    account_data: AccountCreate,
    session=Depends(get_session),
):
    """Create a new financial account."""
    if account_data.account_type not in ACCOUNT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid account_type '{account_data.account_type}'. Must be one of: {ACCOUNT_TYPES}",
        )

    acct = Account(
        user_id=account_data.user_id,
        name=account_data.name,
        account_type=account_data.account_type,
        institution=account_data.institution,
        account_number_masked=account_data.account_number_masked,
        currency=account_data.currency,
        balance=account_data.balance,
        is_active=account_data.is_active,
        icon=account_data.icon,
        color=account_data.color,
        notes=account_data.notes,
    )
    session.add(acct)
    session.commit()
    session.refresh(acct)
    return {
        "id": acct.id,
        "name": acct.name,
        "account_type": acct.account_type,
        "institution": acct.institution,
        "currency": acct.currency,
        "balance": acct.balance,
        "is_active": acct.is_active,
    }


@app.put(f"{settings.API_V1_PREFIX}/accounts/{{account_id}}")
async def update_account(
    account_id: int,
    account_data: AccountUpdate,
    session=Depends(get_session),
):
    """Update an existing account."""
    acct = session.query(Account).filter(Account.id == account_id).first()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")

    update_fields = account_data.dict(exclude_unset=True)
    if "account_type" in update_fields and update_fields["account_type"] not in ACCOUNT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid account_type")

    for key, val in update_fields.items():
        if val is not None:
            setattr(acct, key, val)

    session.commit()
    session.refresh(acct)
    return {"id": acct.id, "name": acct.name, "account_type": acct.account_type, "balance": acct.balance}


@app.delete(f"{settings.API_V1_PREFIX}/accounts/{{account_id}}")
async def delete_account(
    account_id: int,
    session=Depends(get_session),
):
    """Soft-delete an account (set is_active=False)."""
    acct = session.query(Account).filter(Account.id == account_id).first()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    acct.is_active = False
    session.commit()
    return {"message": f"Account '{acct.name}' deactivated", "id": acct.id}


# Transaction endpoints
@app.get(f"{settings.API_V1_PREFIX}/transactions")
async def get_transactions(
    user_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    account_id: Optional[int] = None,
    display_currency: Optional[str] = None,
    include_deleted: bool = False,
    limit: int = 100,
    offset: int = 0,
    session=Depends(get_session)
):
    """Get transactions with optional filters and currency conversion."""
    query = session.query(Transaction).filter(Transaction.user_id == user_id)

    # Exclude soft-deleted unless explicitly requested
    if not include_deleted:
        query = query.filter(
            (Transaction.is_deleted == False) | (Transaction.is_deleted == None)
        )

    if start_date:
        query = query.filter(Transaction.date >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Transaction.date <= datetime.fromisoformat(end_date))
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)

    transactions = query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()

    # Resolve display currency: param > user pref > stored currency
    target_cur = None
    if display_currency:
        target_cur = display_currency.upper()
    else:
        user = session.query(User).filter(User.id == user_id).first()
        if user and hasattr(user, 'preferred_currency') and user.preferred_currency:
            target_cur = user.preferred_currency

    result = []
    for t in transactions:
        amount_display = t.amount
        currency_display = t.currency or "INR"
        if target_cur and target_cur != currency_display:
            try:
                amount_display = currency_service.convert(t.amount, currency_display, target_cur, date=t.date)
                currency_display = target_cur
            except Exception:
                pass

        result.append({
            "id": t.id,
            "description": t.description,
            "amount": round(amount_display, 2),
            "amount_original": t.amount_original,
            "currency": currency_display,
            "currency_original": t.currency_original,
            "exchange_rate": t.exchange_rate,
            "type": t.transaction_type,
            "date": t.date.isoformat(),
            "account": t.account,
            "account_id": t.account_id,
            "reference": t.reference,
            "merchant_name": t.merchant_name,
            "merchant_category": t.merchant_category,
            "transaction_method": t.transaction_method,
            "location": t.location,
            "card_last_four": t.card_last_four,
            "tags": t.tags,
            "notes": t.notes,
            "is_recurring": t.is_recurring,
            "is_duplicate": t.is_duplicate,
            "confidence_score": t.confidence_score,
            "is_deleted": t.is_deleted or False,
            "deleted_at": t.deleted_at.isoformat() if t.deleted_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            "symbol": currency_service.get_symbol(currency_display),
        })

    return {
        "transactions": result,
        "total": len(result),
        "display_currency": target_cur or "INR",
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

    # Audit trail: record creation
    audit = TransactionAudit(
        transaction_id=tx.id,
        user_id=tx.user_id,
        action="create",
        new_value=f"{tx.description} | {tx.amount} {tx.currency}",
    )
    session.add(audit)
    session.commit()

    return TransactionOut.from_orm(tx)


# ─── Transaction Edit endpoint ───
@app.put(f"{settings.API_V1_PREFIX}/transactions/{{transaction_id}}")
async def update_transaction(
    transaction_id: int,
    updates: TransactionUpdate,
    user_id: int = 1,
    session=Depends(get_session),
):
    """Edit a transaction. All fields optional. Tracks changes in audit log."""
    tx = session.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot edit a deleted transaction. Restore it first.")

    update_dict = updates.dict(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field, new_val in update_dict.items():
        old_val = getattr(tx, field, None)
        if old_val != new_val:
            # Audit each changed field
            audit = TransactionAudit(
                transaction_id=tx.id,
                user_id=user_id,
                action="edit",
                field_changed=field,
                old_value=str(old_val) if old_val is not None else None,
                new_value=str(new_val) if new_val is not None else None,
            )
            session.add(audit)
            setattr(tx, field, new_val)

    tx.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(tx)
    return {"status": "updated", "transaction_id": tx.id}


# ─── Transaction Soft-Delete endpoint ───
@app.delete(f"{settings.API_V1_PREFIX}/transactions/{{transaction_id}}")
async def delete_transaction(
    transaction_id: int,
    user_id: int = 1,
    reason: Optional[str] = None,
    session=Depends(get_session),
):
    """Soft-delete a transaction. Financial data is NEVER permanently destroyed."""
    tx = session.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.is_deleted:
        raise HTTPException(status_code=400, detail="Transaction already deleted")

    tx.is_deleted = True
    tx.deleted_at = datetime.utcnow()

    audit = TransactionAudit(
        transaction_id=tx.id,
        user_id=user_id,
        action="delete",
        old_value=f"{tx.description} | {tx.amount} {tx.currency}",
        notes=reason,
    )
    session.add(audit)
    session.commit()
    return {"status": "deleted", "transaction_id": tx.id, "message": "Transaction moved to trash. It can be restored."}


# ─── Transaction Restore endpoint ───
@app.post(f"{settings.API_V1_PREFIX}/transactions/{{transaction_id}}/restore")
async def restore_transaction(
    transaction_id: int,
    user_id: int = 1,
    session=Depends(get_session),
):
    """Restore a soft-deleted transaction."""
    tx = session.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if not tx.is_deleted:
        raise HTTPException(status_code=400, detail="Transaction is not deleted")

    tx.is_deleted = False
    tx.deleted_at = None
    tx.updated_at = datetime.utcnow()

    audit = TransactionAudit(
        transaction_id=tx.id,
        user_id=user_id,
        action="restore",
        new_value=f"{tx.description} | {tx.amount} {tx.currency}",
    )
    session.add(audit)
    session.commit()
    return {"status": "restored", "transaction_id": tx.id}


# ─── Transaction Trash (deleted items) ───
@app.get(f"{settings.API_V1_PREFIX}/transactions/trash")
async def get_deleted_transactions(
    user_id: int = 1,
    display_currency: Optional[str] = None,
    session=Depends(get_session),
):
    """Get all soft-deleted transactions for recovery."""
    txns = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.is_deleted == True,
    ).order_by(Transaction.deleted_at.desc()).all()

    target_cur = display_currency.upper() if display_currency else "INR"

    result = []
    for t in txns:
        amount_display = t.amount
        currency_display = t.currency or "INR"
        if target_cur != currency_display:
            try:
                amount_display = currency_service.convert(t.amount, currency_display, target_cur, date=t.date)
                currency_display = target_cur
            except Exception:
                pass
        result.append({
            "id": t.id,
            "description": t.description,
            "amount": round(amount_display, 2),
            "currency": currency_display,
            "type": t.transaction_type,
            "date": t.date.isoformat(),
            "account": t.account,
            "merchant_name": t.merchant_name,
            "deleted_at": t.deleted_at.isoformat() if t.deleted_at else None,
            "symbol": currency_service.get_symbol(currency_display),
        })

    return {"transactions": result, "total": len(result)}


# ─── Transaction Audit History ───
@app.get(f"{settings.API_V1_PREFIX}/transactions/{{transaction_id}}/history")
async def get_transaction_history(
    transaction_id: int,
    user_id: int = 1,
    session=Depends(get_session),
):
    """Get full audit trail for a transaction."""
    tx = session.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    audits = session.query(TransactionAudit).filter(
        TransactionAudit.transaction_id == transaction_id,
    ).order_by(TransactionAudit.timestamp.desc()).all()

    return {
        "transaction_id": transaction_id,
        "history": [
            {
                "id": a.id,
                "action": a.action,
                "field_changed": a.field_changed,
                "old_value": a.old_value,
                "new_value": a.new_value,
                "timestamp": a.timestamp.isoformat(),
                "notes": a.notes,
            }
            for a in audits
        ],
    }


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
    months: int = 6,
    display_currency: Optional[str] = None,
    session=Depends(get_session)
):
    """Get monthly cash-flow trend for the chart."""
    from datetime import timedelta
    from sqlalchemy import func, extract

    now = datetime.now()
    # Go back `months` months from the 1st of current month
    start_month = now.month - months + 1
    start_year = now.year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date_dt = datetime(start_year, start_month, 1)

    txs = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date_dt,
        (Transaction.is_deleted == False) | (Transaction.is_deleted == None)
    ).all()

    # Resolve currency
    target_cur = display_currency.upper() if display_currency else None
    if not target_cur:
        user = session.query(User).filter(User.id == user_id).first()
        if user and hasattr(user, 'preferred_currency') and user.preferred_currency:
            target_cur = user.preferred_currency
    if not target_cur:
        target_cur = "INR"

    # Group by year-month, converting each transaction to target currency
    monthly: dict = {}
    for t in txs:
        key = t.date.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"income": 0.0, "expenses": 0.0}

        tx_currency = (t.currency or "INR").upper()
        amt = t.amount or 0.0
        if tx_currency != target_cur:
            try:
                amt = currency_service.convert(amt, tx_currency, target_cur, date=t.date)
            except Exception:
                pass

        if t.transaction_type == "income":
            monthly[key]["income"] += amt
        else:
            monthly[key]["expenses"] += abs(amt)

    # Build ordered list for all months in range
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    result = []
    y, m = start_year, start_month
    for _ in range(months):
        key = f"{y}-{m:02d}"
        data = monthly.get(key, {"income": 0.0, "expenses": 0.0})
        result.append({
            "month": month_labels[m - 1],
            "key": key,
            "income": round(data["income"], 2),
            "expenses": round(data["expenses"], 2),
        })
        m += 1
        if m > 12:
            m = 1
            y += 1

    return {
        "trend": result,
        "currency": target_cur,
        "symbol": currency_service.get_symbol(target_cur),
    }


@app.get(f"{settings.API_V1_PREFIX}/analytics/categories")
async def get_spending_by_category(
    user_id: int,
    months: int = 6,
    display_currency: Optional[str] = None,
    session=Depends(get_session),
):
    """Get spending breakdown by merchant/description category."""
    now = datetime.now()
    start_month = now.month - months + 1
    start_year = now.year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date_dt = datetime(start_year, start_month, 1)

    txs = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date_dt,
        Transaction.transaction_type == "expense",
        (Transaction.is_deleted == False) | (Transaction.is_deleted == None),
    ).all()

    target_cur = display_currency.upper() if display_currency else None
    if not target_cur:
        user = session.query(User).filter(User.id == user_id).first()
        if user and hasattr(user, 'preferred_currency') and user.preferred_currency:
            target_cur = user.preferred_currency
    if not target_cur:
        target_cur = "INR"

    # Group by merchant_category or first word of description
    cats: dict = {}
    for t in txs:
        cat = t.merchant_category or (t.description.split(',')[0].split()[0] if t.description else "Other")
        if len(cat) > 30:
            cat = cat[:30]

        tx_currency = (t.currency or "INR").upper()
        amt = abs(t.amount or 0.0)
        if tx_currency != target_cur:
            try:
                amt = abs(currency_service.convert(t.amount, tx_currency, target_cur, date=t.date))
            except Exception:
                pass

        cats[cat] = cats.get(cat, 0.0) + amt

    # Sort by amount descending, take top 8, group rest as "Other"
    sorted_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)
    top = sorted_cats[:8]
    other_total = sum(v for _, v in sorted_cats[8:])
    if other_total > 0:
        top.append(("Other", other_total))

    colors = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899", "#64748b"]

    return {
        "categories": [
            {"name": name, "value": round(val, 2), "color": colors[i % len(colors)]}
            for i, (name, val) in enumerate(top)
        ],
        "currency": target_cur,
        "symbol": currency_service.get_symbol(target_cur),
    }


@app.get(f"{settings.API_V1_PREFIX}/transactions/export")
async def export_transactions(
    user_id: int = 1,
    session=Depends(get_session),
):
    """Export all transactions as CSV."""
    from fastapi.responses import StreamingResponse
    import io
    import csv

    txs = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        (Transaction.is_deleted == False) | (Transaction.is_deleted == None),
    ).order_by(Transaction.date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Amount", "Currency", "Type", "Account", "Merchant", "Reference"])
    for t in txs:
        writer.writerow([
            t.date.isoformat() if t.date else "",
            t.description or "",
            t.amount,
            t.currency or "",
            t.transaction_type or "",
            t.account or "",
            t.merchant_name or "",
            t.reference or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=arthsutra_transactions_{datetime.now().strftime('%Y%m%d')}.csv"},
    )


@app.get(f"{settings.API_V1_PREFIX}/analytics/networth")
async def get_networth(
    user_id: int = 1,
    date: Optional[str] = None,
    session=Depends(get_session)
):
    """Get net-worth calculation."""
    try:
        # Get all assets for the user
        assets = session.query(Asset).filter(Asset.user_id == user_id).all()
        
        # Get all accounts for the user
        accounts = session.query(Account).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).all()
        
        # Calculate total assets value
        total_assets = sum(asset.current_value for asset in assets)
        
        # Add account balances to total assets
        total_account_balance = sum(account.balance for account in accounts)
        total_assets += total_account_balance
        
        # Get all transactions to calculate net position
        transactions = session.query(Transaction).filter(
            Transaction.user_id == user_id,
            (Transaction.is_deleted == False) | (Transaction.is_deleted == None)
        ).all()
        
        # Calculate net income/expenses
        total_income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')
        net_cashflow = total_income - total_expenses
        
        # Calculate net worth
        net_worth = total_assets + net_cashflow
        
        return {
            "user_id": user_id,
            "date": date or datetime.now().isoformat(),
            "net_worth": round(net_worth, 2),
            "total_assets": round(total_assets, 2),
            "total_account_balance": round(total_account_balance, 2),
            "net_cashflow": round(net_cashflow, 2),
            "asset_count": len(assets),
            "account_count": len(accounts)
        }
    except Exception as e:
        logger.error(f"Error calculating net-worth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating net-worth: {str(e)}"
        )


@app.get(f"{settings.API_V1_PREFIX}/analytics/budget")
async def get_budget_analysis(
    user_id: int = 1,
    period: str = "monthly",
    session=Depends(get_session)
):
    """Get budget utilization analysis."""
    try:
        # Get all budgets for the user
        budgets = session.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.is_active == True
        ).all()
        
        if not budgets:
            return {
                "user_id": user_id,
                "period": period,
                "budgets": [],
                "total_budget": 0,
                "total_spent": 0,
                "total_remaining": 0,
                "utilization_rate": 0
            }
        
        # Calculate budget utilization
        budget_analysis = []
        total_budget_amount = 0
        total_spent_amount = 0
        
        for budget in budgets:
            # Get transactions for this budget's category
            transactions = session.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == budget.category_id,
                Transaction.transaction_type == 'expense',
                (Transaction.is_deleted == False) | (Transaction.is_deleted == None)
            ).all()
            
            spent = sum(t.amount for t in transactions)
            remaining = budget.amount - spent
            utilization = (spent / budget.amount * 100) if budget.amount > 0 else 0
            
            category = session.query(Category).filter(Category.id == budget.category_id).first()
            category_name = category.name if category else "Unknown"
            
            budget_analysis.append({
                "budget_id": budget.id,
                "category": category_name,
                "budget_amount": round(budget.amount, 2),
                "spent": round(spent, 2),
                "remaining": round(remaining, 2),
                "utilization_rate": round(utilization, 2),
                "status": "exceeded" if spent > budget.amount else "on_track" if utilization > 80 else "healthy"
            })
            
            total_budget_amount += budget.amount
            total_spent_amount += spent
        
        total_remaining = total_budget_amount - total_spent_amount
        overall_utilization = (total_spent_amount / total_budget_amount * 100) if total_budget_amount > 0 else 0
        
        return {
            "user_id": user_id,
            "period": period,
            "budgets": budget_analysis,
            "total_budget": round(total_budget_amount, 2),
            "total_spent": round(total_spent_amount, 2),
            "total_remaining": round(total_remaining, 2),
            "utilization_rate": round(overall_utilization, 2)
        }
    except Exception as e:
        logger.error(f"Error analyzing budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing budget: {str(e)}"
        )


@app.get(f"{settings.API_V1_PREFIX}/analytics/summary")
async def get_analytics_summary(
    user_id: int,
    display_currency: Optional[str] = None,
    session=Depends(get_session)
):
    """Get analytics summary for a user, optionally converted to display_currency."""
    txs = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        (Transaction.is_deleted == False) | (Transaction.is_deleted == None)
    ).all()

    # Resolve target currency
    target_cur = display_currency.upper() if display_currency else None
    if not target_cur:
        user = session.query(User).filter(User.id == user_id).first()
        if user and hasattr(user, 'preferred_currency') and user.preferred_currency:
            target_cur = user.preferred_currency
    if not target_cur:
        target_cur = "INR"

    # Convert each transaction to target currency individually
    total_income = 0.0
    total_expenses = 0.0
    for t in txs:
        tx_currency = (t.currency or "INR").upper()
        amt = t.amount or 0.0
        if tx_currency != target_cur:
            try:
                amt = currency_service.convert(amt, tx_currency, target_cur, date=t.date)
            except Exception:
                pass  # keep original amount if conversion fails
        if t.transaction_type == 'income':
            total_income += amt
        else:
            total_expenses += abs(amt)

    net_cashflow = total_income - total_expenses
    savings_rate = (net_cashflow / total_income) * 100 if total_income else 0

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_cashflow": round(net_cashflow, 2),
        "savings_rate": round(savings_rate, 2),
        "currency": target_cur,
        "symbol": currency_service.get_symbol(target_cur),
    }


# Forecasting endpoints
@app.get(f"{settings.API_V1_PREFIX}/forecasting/expenses")
async def forecast_expenses_endpoint(
    user_id: int = 1,
    horizon_days: int = 30,
    session=Depends(get_session)
):
    """Get expense forecasting."""
    try:
        # Call the forecasting function from analytics module
        forecast_result = forecast_expenses_fn(
            user_id=user_id,
            horizon_days=horizon_days,
            session=session
        )
        
        # Check if there was an error
        if isinstance(forecast_result, dict) and 'error' in forecast_result:
            return {
                "user_id": user_id,
                "horizon_days": horizon_days,
                "forecast": [],
                "message": forecast_result.get('error', 'Unable to generate forecast')
            }
        
        return {
            "user_id": user_id,
            "horizon_days": horizon_days,
            **forecast_result
        }
    except Exception as e:
        logger.error(f"Error forecasting expenses: {e}")
        # Return a graceful fallback instead of raising an error
        return {
            "user_id": user_id,
            "horizon_days": horizon_days,
            "forecast": [],
            "message": f"Unable to generate forecast: {str(e)}"
        }


@app.get(f"{settings.API_V1_PREFIX}/forecasting/savings")
async def forecast_savings_endpoint(
    user_id: int = 1,
    horizon_days: int = 30,
    session=Depends(get_session)
):
    """Get savings trajectory forecasting."""
    try:
        # Call the forecasting function from analytics module
        forecast_result = forecast_savings_fn(
            user_id=user_id,
            horizon_days=horizon_days,
            session=session
        )
        
        return {
            "user_id": user_id,
            "horizon_days": horizon_days,
            **forecast_result
        }
    except Exception as e:
        logger.error(f"Error forecasting savings: {e}")
        # Return a graceful fallback instead of raising an error
        return {
            "user_id": user_id,
            "horizon_days": horizon_days,
            "monthly_savings": 0,
            "forecast": [],
            "message": f"Unable to generate forecast: {str(e)}"
        }


@app.get(f"{settings.API_V1_PREFIX}/forecasting/retirement")
async def retirement_simulator_endpoint(
    user_id: int = 1,
    current_age: int = 30,
    retirement_age: int = 60,
    monthly_contribution: float = 10000,
    current_savings: float = 0,
    expected_return: float = 0.08,
    inflation_rate: float = 0.06,
    session=Depends(get_session)
):
    """Run retirement corpus simulator."""
    try:
        # Create retirement simulator instance
        simulator = RetirementSimulator()
        
        # Run simulation
        simulation_result = simulator.simulate(
            current_age=current_age,
            retirement_age=retirement_age,
            monthly_contribution=monthly_contribution,
            current_savings=current_savings,
            expected_return=expected_return,
            inflation_rate=inflation_rate
        )
        
        return {
            "user_id": user_id,
            **simulation_result
        }
    except Exception as e:
        logger.error(f"Error running retirement simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running retirement simulation: {str(e)}"
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