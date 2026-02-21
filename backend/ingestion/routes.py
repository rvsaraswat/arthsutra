from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import logging
from ..models import get_session, User, Transaction, TransactionAudit, Account
from ..schemas import TransactionCreate, TransactionOut
from .processor import processor
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/ingestion", tags=["ingestion"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    target_currency: Optional[str] = Form(None),
):
    """
    Uploads a bank statement (PDF/CSV) and returns parsed transactions + detected bank info.
    Does NOT save to database yet.
    """
    user_id = 1

    # Determine target currency: form param > user preference > INR default
    display_currency = "INR"
    if target_currency:
        display_currency = target_currency.upper()
    else:
        try:
            session = get_session()
            user = session.query(User).filter(User.id == user_id).first()
            if user and hasattr(user, 'preferred_currency') and user.preferred_currency:
                display_currency = user.preferred_currency
            session.close()
        except Exception:
            pass

    try:
        logger.info(f"Processing upload: {file.filename} (content_type={file.content_type})")
        transactions, detection_info = await processor.process_file(
            file, user_id, password=password, target_currency=display_currency
        )
        # Sanitize NaN/Inf values from dicts before JSON serialization
        import math
        def sanitize(obj):
            if isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return obj
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize(i) for i in obj]
            return obj

        txn_dicts = [sanitize(t.model_dump()) for t in transactions]
        logger.info(f"Upload complete: {len(txn_dicts)} transactions extracted from {file.filename}")
        return {
            "transactions": txn_dicts,
            "detection": detection_info,
        }
    except Exception as e:
        import traceback
        logger.error(f"Upload failed for {file.filename}: {e}\n{traceback.format_exc()}")
        detail = str(e)
        if not detail or detail == "None":
            detail = f"Failed to parse {file.filename}. The file may be corrupted, password-protected, or in an unsupported format."
        raise HTTPException(status_code=400, detail=detail)


@router.post("/confirm", response_model=List[TransactionOut])
async def confirm_import(
    transactions: List[TransactionCreate],
    bank_name: Optional[str] = None,
    account_type: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """
    Saves a batch of transactions to the database.
    If bank_name + account_type provided and no account_id on transactions,
    auto-create or match an account.
    """
    # ─── Auto-resolve or create account ───
    resolved_account_id = None
    if transactions and transactions[0].account_id:
        resolved_account_id = transactions[0].account_id
    elif bank_name and account_type:
        user_id = transactions[0].user_id if transactions else 1
        currency = transactions[0].currency if transactions else "INR"
        # Try to find existing account matching bank + type
        existing = db.query(Account).filter(
            Account.user_id == user_id,
            Account.institution == bank_name,
            Account.account_type == account_type,
            Account.is_active == True,
        ).first()
        if existing:
            resolved_account_id = existing.id
        else:
            # Auto-create account
            new_account = Account(
                user_id=user_id,
                name=f"{bank_name} {account_type.replace('_', ' ').title()}",
                account_type=account_type,
                institution=bank_name,
                currency=currency,
                balance=0.0,
                is_active=True,
            )
            db.add(new_account)
            db.commit()
            db.refresh(new_account)
            resolved_account_id = new_account.id

    saved_txns = []
    for txn_data in transactions:
        db_txn = Transaction(
            user_id=txn_data.user_id,
            category_id=txn_data.category_id,
            account_id=txn_data.account_id or resolved_account_id,
            description=txn_data.description,
            amount=txn_data.amount,
            currency=txn_data.currency,
            transaction_type=txn_data.transaction_type,
            date=txn_data.date,
            account=txn_data.account or bank_name,
            reference=txn_data.reference,
            is_recurring=txn_data.is_recurring,
            is_duplicate=txn_data.is_duplicate,
            confidence_score=txn_data.confidence_score,

            # Currency metadata
            amount_original=txn_data.amount_original,
            currency_original=txn_data.currency_original,
            exchange_rate=txn_data.exchange_rate,
            source=txn_data.source,
            source_file=txn_data.source_file,
            raw_data=txn_data.raw_data,

            # Enriched metadata
            merchant_name=txn_data.merchant_name,
            merchant_category=txn_data.merchant_category,
            transaction_method=txn_data.transaction_method,
            location=txn_data.location,
            card_last_four=txn_data.card_last_four,
            metadata_json=txn_data.metadata_json,

            tags=txn_data.tags,
            notes=txn_data.notes,
        )
        db.add(db_txn)
        saved_txns.append(db_txn)

    try:
        db.commit()
        # Create audit trail entries for all imported transactions
        for t in saved_txns:
            db.refresh(t)
            audit = TransactionAudit(
                transaction_id=t.id,
                user_id=t.user_id,
                action="create",
                new_value=f"Import: {t.description} | {t.amount} {t.currency}",
                notes=f"Imported from {t.source_file or t.source or 'file'}",
            )
            db.add(audit)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return saved_txns
