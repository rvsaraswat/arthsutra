"""
Accounting API routes — double-entry ledger, validation, reporting,
and AI classification endpoints.

All endpoints live under /api/v1/accounting/...
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..models import (
    Transaction,
    Account,
    LedgerEntry,
    get_session,
)
from ..schemas import (
    AccountingTransactionCreate,
    ClassificationRequest,
    ClassificationResponse,
    LedgerEntryOut,
    UXHintsResponse,
    ValidationRequest,
    ValidationResponse,
    BalanceSheetResponse,
    OutstandingLoansResponse,
    TransactionNatureEnum,
    TransactionTypeEnum,
)
from .enums import (
    AccountingType,
    TransactionNature,
    TransactionType,
    infer_accounting_type,
)
from .validation import (
    TransactionInput,
    ValidationError,
    validate_transaction,
    validate_transaction_soft,
    get_ux_hints,
)
from .ledger import LedgerEngine
from .reports import ReportingEngine
from .classifier import TransactionClassifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/accounting", tags=["accounting"])

# Singletons
_ledger = LedgerEngine()
_classifier = TransactionClassifier()
_reports = ReportingEngine()


# ─── Dependency ─────────────────────────────────────────────────────────────

def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
#  TRANSACTION CRUD (accounting-aware)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/transactions", status_code=201)
def create_accounting_transaction(
    payload: AccountingTransactionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a transaction with full accounting validation and double-entry
    ledger generation.
    """
    # Resolve account types for validation
    from_acct_type = None
    to_acct_type = None
    if payload.from_account_id:
        acct = db.query(Account).get(payload.from_account_id)
        if not acct:
            raise HTTPException(404, f"from_account_id {payload.from_account_id} not found")
        from_acct_type = acct.account_type
    if payload.to_account_id:
        acct = db.query(Account).get(payload.to_account_id)
        if not acct:
            raise HTTPException(404, f"to_account_id {payload.to_account_id} not found")
        to_acct_type = acct.account_type

    # Validate
    txn_input = TransactionInput(
        transaction_type=TransactionType(payload.transaction_type.value),
        transaction_nature=TransactionNature(payload.transaction_nature.value),
        amount=payload.amount,
        currency=payload.currency,
        from_account_id=payload.from_account_id,
        to_account_id=payload.to_account_id,
        from_account_type=from_acct_type,
        to_account_type=to_acct_type,
        category=payload.category,
        counterparty=payload.counterparty,
    )

    try:
        validate_transaction(txn_input)
    except ValidationError as e:
        raise HTTPException(422, detail={"errors": e.errors})

    # Determine account_id (primary — for backward compatibility)
    account_id = payload.to_account_id or payload.from_account_id

    # Create Transaction
    txn = Transaction(
        user_id=payload.user_id,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        transaction_type=payload.transaction_type.value,
        transaction_nature=payload.transaction_nature.value,
        date=payload.date,
        from_account_id=payload.from_account_id,
        to_account_id=payload.to_account_id,
        counterparty=payload.counterparty,
        account_id=account_id,
        category_id=payload.category_id,
        merchant_category=payload.category,
        notes=payload.notes,
        tags=payload.tags,
        reference=payload.reference,
        source="manual",
    )
    db.add(txn)
    db.flush()  # get txn.id

    # Generate ledger entries
    entries = _ledger.create_entries(
        transaction_id=txn.id,
        txn_type=TransactionType(payload.transaction_type.value),
        txn_nature=TransactionNature(payload.transaction_nature.value),
        amount=payload.amount,
        date=payload.date,
        description=payload.description,
        from_account_id=payload.from_account_id,
        from_account_type=from_acct_type,
        to_account_id=payload.to_account_id,
        to_account_type=to_acct_type,
    )

    for entry_dto in entries:
        le = LedgerEntry(
            transaction_id=entry_dto.transaction_id,
            account_id=entry_dto.account_id if entry_dto.account_id != 0 else None,
            debit=entry_dto.debit,
            credit=entry_dto.credit,
            entry_date=entry_dto.entry_date or payload.date,
            description=entry_dto.description,
        )
        db.add(le)

    # Update account balances
    _update_account_balances(db, txn)

    db.commit()
    db.refresh(txn)

    logger.info(
        "Created accounting txn #%s: %s %s (%s/%s)",
        txn.id, payload.transaction_type.value,
        payload.transaction_nature.value, payload.amount, payload.currency,
    )

    return {
        "id": txn.id,
        "transaction_type": txn.transaction_type,
        "transaction_nature": txn.transaction_nature,
        "amount": txn.amount,
        "ledger_entries": len(entries),
    }


# ─── Get ledger entries for a transaction ───────────────────────────────────

@router.get("/transactions/{transaction_id}/ledger", response_model=list[LedgerEntryOut])
def get_transaction_ledger(
    transaction_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Return the double-entry ledger entries for a specific transaction."""
    txn = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.user_id == user_id)
        .first()
    )
    if not txn:
        raise HTTPException(404, "Transaction not found")

    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.transaction_id == transaction_id)
        .all()
    )
    return entries


# ═══════════════════════════════════════════════════════════════════════════
#  VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/validate", response_model=ValidationResponse)
def validate_transaction_endpoint(
    payload: ValidationRequest,
    db: Session = Depends(get_db),
):
    """
    Pre-submit validation.  Returns {valid: true/false, errors: [...]}.
    Call this from the frontend before submitting a transaction.
    """
    txn_input = TransactionInput(
        transaction_type=TransactionType(payload.transaction_type),
        transaction_nature=TransactionNature(payload.transaction_nature),
        amount=payload.amount,
        currency=payload.currency,
        from_account_id=payload.from_account_id,
        to_account_id=payload.to_account_id,
        from_account_type=payload.from_account_type,
        to_account_type=payload.to_account_type,
        category=payload.category,
        counterparty=payload.counterparty,
    )

    errors = validate_transaction_soft(txn_input)
    return ValidationResponse(valid=len(errors) == 0, errors=errors)


# ═══════════════════════════════════════════════════════════════════════════
#  UX HINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/ux-hints", response_model=UXHintsResponse)
def get_ux_hints_endpoint(
    transaction_type: str = Query(...),
    transaction_nature: str = Query(...),
):
    """
    Return UX hints for the transaction form:
      - show_category
      - require_counterparty
      - require_both_accounts
      - affects_net_worth
    """
    try:
        txn_type = TransactionType(transaction_type)
        txn_nature = TransactionNature(transaction_nature)
    except ValueError as e:
        raise HTTPException(400, str(e))

    hints = get_ux_hints(txn_type, txn_nature)
    return UXHintsResponse(**hints)


# ═══════════════════════════════════════════════════════════════════════════
#  AI CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/classify", response_model=ClassificationResponse)
def classify_transaction(payload: ClassificationRequest):
    """
    Auto-classify a transaction description into type + nature.
    """
    result = _classifier.classify(
        description=payload.description,
        amount=payload.amount,
        from_account_type=payload.from_account_type,
        to_account_type=payload.to_account_type,
    )
    return ClassificationResponse(
        transaction_type=result.transaction_type.value,
        transaction_nature=result.transaction_nature.value,
        confidence=result.confidence,
        reasoning=result.reasoning,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  REPORTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/reports/cashflow")
def report_cash_flow(
    user_id: int = Query(...),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    months: int = Query(6),
    db: Session = Depends(get_db),
):
    """Cash flow report — all money movements."""
    end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
    start = (
        datetime.fromisoformat(start_date)
        if start_date
        else end - timedelta(days=months * 31)
    )
    return _reports.get_cash_flow(db, user_id, start, end)


@router.get("/reports/income-expense")
def report_income_expense(
    user_id: int = Query(...),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    months: int = Query(6),
    db: Session = Depends(get_db),
):
    """Income & expense summary — excludes transfers."""
    end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
    start = (
        datetime.fromisoformat(start_date)
        if start_date
        else end - timedelta(days=months * 31)
    )
    return _reports.get_income_expense_summary(db, user_id, start, end)


@router.get("/reports/balance-sheet", response_model=BalanceSheetResponse)
def report_balance_sheet(
    user_id: int = Query(...),
    as_of: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Point-in-time balance sheet: Assets - Liabilities = Net Worth."""
    date = datetime.fromisoformat(as_of) if as_of else datetime.utcnow()
    return _reports.get_balance_sheet(db, user_id, date)


@router.get("/reports/outstanding-loans", response_model=OutstandingLoansResponse)
def report_outstanding_loans(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """All open loans — given and received."""
    return _reports.get_outstanding_loans(db, user_id)


@router.get("/reports/net-worth-timeline")
def report_net_worth_timeline(
    user_id: int = Query(...),
    months: int = Query(12),
    db: Session = Depends(get_db),
):
    """Monthly net-worth snapshots."""
    return _reports.get_net_worth_timeline(db, user_id, months)


# ═══════════════════════════════════════════════════════════════════════════
#  ENUM REFERENCE
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/enums")
def get_accounting_enums():
    """Return all accounting enums for frontend dropdowns."""
    return {
        "transaction_types": [t.value for t in TransactionType],
        "transaction_natures": {
            t.value: [n.value for n in natures]
            for t, natures in {
                TransactionType.INCOME: [
                    TransactionNature.SALARY,
                    TransactionNature.BUSINESS_INCOME,
                    TransactionNature.INVESTMENT_INCOME,
                    TransactionNature.GIFT_RECEIVED,
                    TransactionNature.REFUND,
                    TransactionNature.OTHER_INCOME,
                ],
                TransactionType.EXPENSE: [
                    TransactionNature.PURCHASE,
                    TransactionNature.SUBSCRIPTION,
                    TransactionNature.BILL_PAYMENT,
                    TransactionNature.REIMBURSEMENT_PAID,
                    TransactionNature.GIFT_GIVEN,
                    TransactionNature.OTHER_EXPENSE,
                ],
                TransactionType.TRANSFER: [
                    TransactionNature.INTERNAL_TRANSFER,
                    TransactionNature.CC_BILL_PAYMENT,
                    TransactionNature.REIMBURSEMENT_RECEIVED,
                    TransactionNature.LOAN_GIVEN,
                    TransactionNature.LOAN_RECEIVED,
                    TransactionNature.LOAN_REPAID,
                    TransactionNature.ADJUSTMENT,
                ],
            }.items()
        },
        "accounting_types": [t.value for t in AccountingType],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _update_account_balances(db: Session, txn: Transaction) -> None:
    """
    Update real account balances after a transaction is created.

    For transfers: decrease source, increase destination.
    For income: increase to_account.
    For expense: decrease from_account.
    """
    amount = abs(txn.amount)

    if txn.transaction_type == "transfer":
        if txn.from_account_id:
            src = db.query(Account).get(txn.from_account_id)
            if src:
                acct_type = infer_accounting_type(src.account_type)
                if acct_type in (AccountingType.ASSET, AccountingType.RECEIVABLE):
                    src.balance -= amount
                else:
                    src.balance += amount  # Paying off liability reduces it
        if txn.to_account_id:
            dst = db.query(Account).get(txn.to_account_id)
            if dst:
                acct_type = infer_accounting_type(dst.account_type)
                if acct_type in (AccountingType.ASSET, AccountingType.RECEIVABLE):
                    dst.balance += amount
                else:
                    dst.balance += amount

    elif txn.transaction_type == "income":
        acct_id = txn.to_account_id or txn.account_id
        if acct_id:
            acct = db.query(Account).get(acct_id)
            if acct:
                acct.balance += amount

    elif txn.transaction_type == "expense":
        acct_id = txn.from_account_id or txn.account_id
        if acct_id:
            acct = db.query(Account).get(acct_id)
            if acct:
                acct.balance -= amount
