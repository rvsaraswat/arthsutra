"""
Arthsutra Accounting Engine
===========================
Double-entry, accounting-correct core for personal finance.

Key principles:
  1. Separate cash movement from economic impact
  2. Transfers do NOT change net worth
  3. Loans, reimbursements, and internal transfers are NOT income or expense
  4. Every transaction generates balanced debit/credit ledger entries
"""

from .enums import TransactionType, TransactionNature, AccountingType
from .validation import validate_transaction, ValidationError
from .ledger import LedgerEngine
from .reports import ReportingEngine
from .classifier import TransactionClassifier

__all__ = [
    "TransactionType",
    "TransactionNature",
    "AccountingType",
    "validate_transaction",
    "ValidationError",
    "LedgerEngine",
    "ReportingEngine",
    "TransactionClassifier",
]
