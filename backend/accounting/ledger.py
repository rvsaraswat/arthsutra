"""
Double-entry ledger engine.

Every transaction generates exactly TWO balanced ledger entries
(total debits == total credits).

Accounting conventions:
  Assets      increase → Debit    decrease → Credit
  Liabilities increase → Credit   decrease → Debit
  Receivables increase → Debit    decrease → Credit
  Payables    increase → Credit   decrease → Debit
  Income      recorded as         Credit
  Expenses    recorded as         Debit
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .enums import (
    AccountingType,
    TransactionNature,
    TransactionType,
    infer_accounting_type,
)

logger = logging.getLogger(__name__)


# ─── Ledger entry DTO ──────────────────────────────────────────────────────

@dataclass
class LedgerEntryDTO:
    """In-memory representation before persistence."""

    transaction_id: int
    account_id: int
    debit: float = 0.0
    credit: float = 0.0
    entry_date: Optional[datetime] = None
    description: str = ""


# ─── Engine ─────────────────────────────────────────────────────────────────

class LedgerEngine:
    """
    Generates balanced debit/credit ledger entries for any transaction.

    Usage::

        engine = LedgerEngine()
        entries = engine.create_entries(
            transaction_id=42,
            txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.INTERNAL_TRANSFER,
            amount=5000.0,
            from_account_id=1,
            to_account_id=2,
            from_account_type="savings",
            to_account_type="current",
            date=datetime.utcnow(),
        )
        # entries → [debit entry, credit entry]
    """

    # ── public ──────────────────────────────────────────────────────────

    def create_entries(
        self,
        transaction_id: int,
        txn_type: TransactionType,
        txn_nature: TransactionNature,
        amount: float,
        date: datetime,
        description: str = "",
        # For INCOME, to_account is the account that receives money
        to_account_id: Optional[int] = None,
        to_account_type: Optional[str] = None,
        # For EXPENSE, from_account is the account money leaves
        from_account_id: Optional[int] = None,
        from_account_type: Optional[str] = None,
        # For TRANSFER, both are needed
    ) -> list[LedgerEntryDTO]:
        """
        Generate balanced ledger entries.  Returns list of 2 entries
        whose total debit == total credit.
        """
        entries: list[LedgerEntryDTO] = []

        if txn_type == TransactionType.INCOME:
            entries = self._income_entries(
                transaction_id, amount, to_account_id, to_account_type,
                date, description,
            )
        elif txn_type == TransactionType.EXPENSE:
            entries = self._expense_entries(
                transaction_id, amount, from_account_id, from_account_type,
                date, description,
            )
        elif txn_type == TransactionType.TRANSFER:
            entries = self._transfer_entries(
                transaction_id, txn_nature, amount,
                from_account_id, from_account_type,
                to_account_id, to_account_type,
                date, description,
            )

        # Sanity check: debits == credits
        total_debit = sum(e.debit for e in entries)
        total_credit = sum(e.credit for e in entries)
        if abs(total_debit - total_credit) > 0.001:
            logger.error(
                "UNBALANCED ledger for txn %s: debit=%.2f credit=%.2f",
                transaction_id, total_debit, total_credit,
            )
            raise ValueError(
                f"Ledger imbalance: debit={total_debit}, credit={total_credit}"
            )

        return entries

    # ── private helpers ─────────────────────────────────────────────────

    def _income_entries(
        self, txn_id: int, amount: float,
        to_account_id: Optional[int], to_account_type: Optional[str],
        date: datetime, desc: str,
    ) -> list[LedgerEntryDTO]:
        """
        Income:
          Debit  → Asset account (bank balance goes up)
          Credit → Income (equity/retained earnings conceptually)

        We use account_id=0 as a virtual "Income" account for the credit side.
        """
        acct_id = to_account_id or 0
        return [
            LedgerEntryDTO(
                transaction_id=txn_id,
                account_id=acct_id,
                debit=amount,
                credit=0.0,
                entry_date=date,
                description=f"Income: {desc}",
            ),
            LedgerEntryDTO(
                transaction_id=txn_id,
                account_id=0,  # Virtual income account
                debit=0.0,
                credit=amount,
                entry_date=date,
                description=f"Income: {desc}",
            ),
        ]

    def _expense_entries(
        self, txn_id: int, amount: float,
        from_account_id: Optional[int], from_account_type: Optional[str],
        date: datetime, desc: str,
    ) -> list[LedgerEntryDTO]:
        """
        Expense:
          Debit  → Expense (reduces equity)
          Credit → Asset account (bank balance goes down)
        """
        acct_id = from_account_id or 0
        return [
            LedgerEntryDTO(
                transaction_id=txn_id,
                account_id=0,  # Virtual expense account
                debit=amount,
                credit=0.0,
                entry_date=date,
                description=f"Expense: {desc}",
            ),
            LedgerEntryDTO(
                transaction_id=txn_id,
                account_id=acct_id,
                debit=0.0,
                credit=amount,
                entry_date=date,
                description=f"Expense: {desc}",
            ),
        ]

    def _transfer_entries(
        self, txn_id: int, nature: TransactionNature, amount: float,
        from_id: Optional[int], from_type: Optional[str],
        to_id: Optional[int], to_type: Optional[str],
        date: datetime, desc: str,
    ) -> list[LedgerEntryDTO]:
        """
        Transfers — the heart of the ledger.  The accounting impact
        depends on the nature, not just the direction.

        Rules:
          Assets      increase → Debit,  decrease → Credit
          Liabilities increase → Credit, decrease → Debit
          Receivables increase → Debit,  decrease → Credit
          Payables    increase → Credit, decrease → Debit
        """
        from_acct = infer_accounting_type(from_type) if from_type else AccountingType.ASSET
        to_acct = infer_accounting_type(to_type) if to_type else AccountingType.ASSET

        from_acct_id = from_id or 0
        to_acct_id = to_id or 0

        # Determine real accounting impact per nature
        from_increases, to_increases = self._get_transfer_impacts(
            nature, from_acct, to_acct
        )

        if from_increases:
            from_entry = self._increase_entry(
                from_acct, txn_id, from_acct_id, amount, date, desc
            )
        else:
            from_entry = self._decrease_entry(
                from_acct, txn_id, from_acct_id, amount, date, desc
            )

        if to_increases:
            to_entry = self._increase_entry(
                to_acct, txn_id, to_acct_id, amount, date, desc
            )
        else:
            to_entry = self._decrease_entry(
                to_acct, txn_id, to_acct_id, amount, date, desc
            )

        return [from_entry, to_entry]

    @staticmethod
    def _get_transfer_impacts(
        nature: TransactionNature,
        from_acct: AccountingType,
        to_acct: AccountingType,
    ) -> tuple[bool, bool]:
        """
        Determine whether each account INCREASES or DECREASES.

        Returns ``(from_increases, to_increases)``.

        The key insight: paying a liability or repaying a loan DECREASES
        the destination, while receiving a loan INCREASES the source.
        """
        if nature == TransactionNature.INTERNAL_TRANSFER:
            return (False, True)      # from↓ (asset out), to↑ (asset in)

        elif nature == TransactionNature.CC_BILL_PAYMENT:
            return (False, False)     # from↓ (asset), to↓ (liability paid off)

        elif nature == TransactionNature.LOAN_GIVEN:
            return (False, True)      # from↓ (asset out), to↑ (receivable up)

        elif nature == TransactionNature.LOAN_RECEIVED:
            return (True, True)       # from↑ (payable/new debt), to↑ (asset/got cash)

        elif nature == TransactionNature.LOAN_REPAID:
            # Direction depends on account types
            if from_acct == AccountingType.RECEIVABLE:
                # Friend repays me: Receivable↓, Asset↑
                return (False, True)
            else:
                # I repay my debt: Asset↓, Payable↓
                return (False, False)

        elif nature == TransactionNature.REIMBURSEMENT_RECEIVED:
            return (False, True)      # source↓, to↑ (asset)

        elif nature == TransactionNature.ADJUSTMENT:
            return (False, True)      # default: from↓, to↑

        else:
            return (False, True)      # safe default

    def _increase_entry(
        self, acct_type: AccountingType,
        txn_id: int, acct_id: int, amount: float,
        date: datetime, desc: str,
    ) -> LedgerEntryDTO:
        """Create an entry that INCREASES the given account type."""
        if acct_type in (AccountingType.ASSET, AccountingType.RECEIVABLE):
            # Assets / Receivables increase via Debit
            return LedgerEntryDTO(
                transaction_id=txn_id, account_id=acct_id,
                debit=amount, credit=0.0,
                entry_date=date, description=desc,
            )
        else:
            # Liabilities / Payables increase via Credit
            return LedgerEntryDTO(
                transaction_id=txn_id, account_id=acct_id,
                debit=0.0, credit=amount,
                entry_date=date, description=desc,
            )

    def _decrease_entry(
        self, acct_type: AccountingType,
        txn_id: int, acct_id: int, amount: float,
        date: datetime, desc: str,
    ) -> LedgerEntryDTO:
        """Create an entry that DECREASES the given account type."""
        if acct_type in (AccountingType.ASSET, AccountingType.RECEIVABLE):
            # Assets / Receivables decrease via Credit
            return LedgerEntryDTO(
                transaction_id=txn_id, account_id=acct_id,
                debit=0.0, credit=amount,
                entry_date=date, description=desc,
            )
        else:
            # Liabilities / Payables decrease via Debit
            return LedgerEntryDTO(
                transaction_id=txn_id, account_id=acct_id,
                debit=amount, credit=0.0,
                entry_date=date, description=desc,
            )

    # ── balance helpers ─────────────────────────────────────────────────

    @staticmethod
    def account_balance_from_entries(
        entries: list[LedgerEntryDTO],
        account_id: int,
        acct_type: AccountingType,
    ) -> float:
        """
        Compute the balance of an account from its ledger entries.

        For ASSET / RECEIVABLE:  balance = sum(debit) - sum(credit)
        For LIABILITY / PAYABLE: balance = sum(credit) - sum(debit)
        """
        acct_entries = [e for e in entries if e.account_id == account_id]
        total_debit = sum(e.debit for e in acct_entries)
        total_credit = sum(e.credit for e in acct_entries)

        if acct_type in (AccountingType.ASSET, AccountingType.RECEIVABLE):
            return total_debit - total_credit
        else:
            return total_credit - total_debit
