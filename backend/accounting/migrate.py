"""
Migration script: Add accounting columns to existing database and
back-fill transaction_nature + ledger entries for existing data.

This is a one-time migration that:
  1. Adds new columns to accounts and transactions tables
  2. Creates the ledger_entries table
  3. Back-fills accounting_type on accounts
  4. Classifies existing transactions into nature
  5. Generates ledger entries for all existing transactions

Usage:
    cd backend
    python -m accounting.migrate
"""
import sys
import os
import logging
from datetime import datetime

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from models import create_engine_with_encryption, Base, Transaction, Account, get_session
from accounting.enums import (
    TransactionType,
    TransactionNature,
    infer_accounting_type,
)
from accounting.classifier import TransactionClassifier
from accounting.ledger import LedgerEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
logger = logging.getLogger(__name__)


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column already exists in a table."""
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(engine, table_name: str) -> bool:
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate():
    engine = create_engine_with_encryption()

    logger.info("=== Arthsutra Accounting Migration ===")

    # ── Step 1: Schema changes ──────────────────────────────────────────

    with engine.connect() as conn:
        # Accounts: add accounting_type, counterparty
        if not column_exists(engine, "accounts", "accounting_type"):
            conn.execute(text("ALTER TABLE accounts ADD COLUMN accounting_type VARCHAR(20)"))
            logger.info("Added accounts.accounting_type")
        if not column_exists(engine, "accounts", "counterparty"):
            conn.execute(text("ALTER TABLE accounts ADD COLUMN counterparty VARCHAR(200)"))
            logger.info("Added accounts.counterparty")

        # Transactions: add transaction_nature, from_account_id, to_account_id, counterparty
        if not column_exists(engine, "transactions", "transaction_nature"):
            conn.execute(text("ALTER TABLE transactions ADD COLUMN transaction_nature VARCHAR(40)"))
            logger.info("Added transactions.transaction_nature")
        if not column_exists(engine, "transactions", "from_account_id"):
            conn.execute(text("ALTER TABLE transactions ADD COLUMN from_account_id INTEGER REFERENCES accounts(id)"))
            logger.info("Added transactions.from_account_id")
        if not column_exists(engine, "transactions", "to_account_id"):
            conn.execute(text("ALTER TABLE transactions ADD COLUMN to_account_id INTEGER REFERENCES accounts(id)"))
            logger.info("Added transactions.to_account_id")
        if not column_exists(engine, "transactions", "counterparty"):
            conn.execute(text("ALTER TABLE transactions ADD COLUMN counterparty VARCHAR(200)"))
            logger.info("Added transactions.counterparty")

        conn.commit()

    # Create ledger_entries table
    if not table_exists(engine, "ledger_entries"):
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables.get("ledger_entries")])
        logger.info("Created ledger_entries table")
    else:
        logger.info("ledger_entries table already exists")

    # ── Step 2: Back-fill account accounting_type ───────────────────────

    db = get_session()
    try:
        accounts = db.query(Account).all()
        updated_accounts = 0
        for acct in accounts:
            if not acct.accounting_type:
                acct.accounting_type = infer_accounting_type(acct.account_type).value
                updated_accounts += 1
        db.commit()
        logger.info("Updated accounting_type for %d accounts", updated_accounts)

        # ── Step 3: Classify existing transactions ──────────────────────────

        classifier = TransactionClassifier()
        ledger_engine = LedgerEngine()

        transactions = db.query(Transaction).filter(
            Transaction.is_deleted == False
        ).all()

        classified = 0
        ledger_created = 0

        for txn in transactions:
            # Skip if already has nature
            if txn.transaction_nature:
                continue

            # Use classifier to infer nature
            result = classifier.classify(
                description=txn.description,
                amount=txn.amount,
            )

            # If the current type is 'transfer', keep it
            if txn.transaction_type == "transfer":
                txn.transaction_nature = result.transaction_nature.value
            elif txn.transaction_type == "income":
                txn.transaction_nature = result.transaction_nature.value
                if result.transaction_type != TransactionType.INCOME:
                    txn.transaction_nature = TransactionNature.OTHER_INCOME.value
            elif txn.transaction_type == "expense":
                txn.transaction_nature = result.transaction_nature.value
                if result.transaction_type != TransactionType.EXPENSE:
                    txn.transaction_nature = TransactionNature.OTHER_EXPENSE.value
            else:
                txn.transaction_nature = result.transaction_nature.value

            # Set from/to account IDs based on type
            if txn.transaction_type == "income" and txn.account_id:
                txn.to_account_id = txn.account_id
            elif txn.transaction_type == "expense" and txn.account_id:
                txn.from_account_id = txn.account_id
            elif txn.transaction_type == "transfer" and txn.account_id:
                # For transfers, we can't always determine direction from legacy data
                # Default: set both to same account (will need manual correction)
                if not txn.from_account_id:
                    txn.from_account_id = txn.account_id
                if not txn.to_account_id:
                    txn.to_account_id = txn.account_id
                # If both accounts end up the same, force INTERNAL_TRANSFER
                # (other natures require distinct account types)
                if txn.from_account_id == txn.to_account_id:
                    txn.transaction_nature = TransactionNature.INTERNAL_TRANSFER.value

            classified += 1

        db.commit()
        logger.info("Classified %d transactions with transaction_nature", classified)

        # ── Step 4: Generate ledger entries ─────────────────────────────────

        # Only for transactions that don't have ledger entries yet
        from models import LedgerEntry

        for txn in transactions:
            existing = db.query(LedgerEntry).filter(
                LedgerEntry.transaction_id == txn.id
            ).count()
            if existing > 0:
                continue

            try:
                # Determine account types
                from_type = None
                to_type = None
                if txn.from_account_id:
                    acct = db.query(Account).get(txn.from_account_id)
                    if acct:
                        from_type = acct.account_type
                if txn.to_account_id:
                    acct = db.query(Account).get(txn.to_account_id)
                    if acct:
                        to_type = acct.account_type

                entries = ledger_engine.create_entries(
                    transaction_id=txn.id,
                    txn_type=TransactionType(txn.transaction_type),
                    txn_nature=TransactionNature(txn.transaction_nature or "adjustment"),
                    amount=abs(txn.amount),
                    date=txn.date,
                    description=txn.description[:200] if txn.description else "",
                    from_account_id=txn.from_account_id,
                    from_account_type=from_type,
                    to_account_id=txn.to_account_id,
                    to_account_type=to_type,
                )

                for entry_dto in entries:
                    le = LedgerEntry(
                        transaction_id=entry_dto.transaction_id,
                        account_id=entry_dto.account_id if entry_dto.account_id != 0 else None,
                        debit=entry_dto.debit,
                        credit=entry_dto.credit,
                        entry_date=entry_dto.entry_date or txn.date,
                        description=entry_dto.description,
                    )
                    db.add(le)
                ledger_created += 1
            except Exception as e:
                logger.warning("Failed to create ledger for txn #%d: %s", txn.id, e)

        db.commit()
        logger.info("Created ledger entries for %d transactions", ledger_created)

    finally:
        db.close()

    logger.info("=== Migration complete ===")


if __name__ == "__main__":
    migrate()
