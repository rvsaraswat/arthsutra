"""
Transaction validation — enforces accounting correctness before any
transaction is persisted.

Rules implemented:
  • EXPENSE requires a category
  • INCOME must NOT have a fromAccount (money flows in, not out)
  • TRANSFER requires both from_account and to_account
  • Account-type movement restrictions (e.g. Expense → Receivable is invalid)
  • Nature must be valid for its type
  • INTERNAL_TRANSFER: both accounts must be ASSET
  • LOAN_GIVEN: Asset → Receivable
  • LOAN_RECEIVED: Payable → Asset
  • Amounts must be positive
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .enums import (
    AccountingType,
    TransactionNature,
    TransactionType,
    infer_accounting_type,
    is_valid_nature_for_type,
)


class ValidationError(Exception):
    """Raised when a transaction violates accounting rules."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class TransactionInput:
    """Lightweight DTO for pre-validation (not a DB model)."""

    transaction_type: TransactionType
    transaction_nature: TransactionNature
    amount: float
    currency: str = "INR"

    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None

    # Accounting types must be resolved before validation
    from_account_type: Optional[str] = None   # e.g. "savings", "credit_card"
    to_account_type: Optional[str] = None

    category: Optional[str] = None
    counterparty: Optional[str] = None  # Required for loans
    notes: Optional[str] = None


# ─── Rule functions ─────────────────────────────────────────────────────────

def _check_amount(txn: TransactionInput, errors: list[str]) -> None:
    if txn.amount <= 0:
        errors.append("Amount must be positive.")


def _check_nature_type_match(txn: TransactionInput, errors: list[str]) -> None:
    if not is_valid_nature_for_type(txn.transaction_type, txn.transaction_nature):
        errors.append(
            f"Nature '{txn.transaction_nature.value}' is not valid for "
            f"type '{txn.transaction_type.value}'."
        )


def _check_expense_has_category(txn: TransactionInput, errors: list[str]) -> None:
    if txn.transaction_type == TransactionType.EXPENSE and not txn.category:
        errors.append("EXPENSE transactions require a category.")


def _check_income_no_from_account(txn: TransactionInput, errors: list[str]) -> None:
    """Income flows INTO an account; fromAccount should be null."""
    if txn.transaction_type == TransactionType.INCOME and txn.from_account_id:
        errors.append("INCOME transactions must not have a from_account (money flows inward).")


def _check_transfer_has_both_accounts(
    txn: TransactionInput, errors: list[str]
) -> None:
    if txn.transaction_type == TransactionType.TRANSFER:
        if not txn.from_account_id or not txn.to_account_id:
            errors.append(
                "TRANSFER transactions require both from_account and to_account."
            )


def _check_loan_has_counterparty(txn: TransactionInput, errors: list[str]) -> None:
    loan_natures = {
        TransactionNature.LOAN_GIVEN,
        TransactionNature.LOAN_RECEIVED,
        TransactionNature.LOAN_REPAID,
    }
    if txn.transaction_nature in loan_natures and not txn.counterparty:
        errors.append("Loan transactions require a counterparty name.")


def _check_account_type_movements(
    txn: TransactionInput, errors: list[str]
) -> None:
    """Validate that account types make sense for the transaction nature."""
    if txn.transaction_type != TransactionType.TRANSFER:
        return

    if not txn.from_account_type or not txn.to_account_type:
        return  # Can't validate further without account types

    from_acct = infer_accounting_type(txn.from_account_type)
    to_acct = infer_accounting_type(txn.to_account_type)

    nature = txn.transaction_nature

    # INTERNAL_TRANSFER: both must be ASSET
    if nature == TransactionNature.INTERNAL_TRANSFER:
        if from_acct != AccountingType.ASSET or to_acct != AccountingType.ASSET:
            errors.append(
                "INTERNAL_TRANSFER requires both accounts to be ASSET type."
            )

    # CC_BILL_PAYMENT: Asset → Liability
    elif nature == TransactionNature.CC_BILL_PAYMENT:
        if from_acct != AccountingType.ASSET or to_acct != AccountingType.LIABILITY:
            errors.append(
                "CC_BILL_PAYMENT must flow from ASSET to LIABILITY account."
            )

    # LOAN_GIVEN: Asset → Receivable
    elif nature == TransactionNature.LOAN_GIVEN:
        if from_acct != AccountingType.ASSET or to_acct != AccountingType.RECEIVABLE:
            errors.append(
                "LOAN_GIVEN must flow from ASSET to RECEIVABLE account."
            )

    # LOAN_RECEIVED: Payable credited, Asset debited
    elif nature == TransactionNature.LOAN_RECEIVED:
        if from_acct != AccountingType.PAYABLE or to_acct != AccountingType.ASSET:
            errors.append(
                "LOAN_RECEIVED must flow from PAYABLE to ASSET account."
            )

    # LOAN_REPAID: direction depends on who repays
    elif nature == TransactionNature.LOAN_REPAID:
        valid_repayments = [
            (AccountingType.RECEIVABLE, AccountingType.ASSET),   # Friend repays me
            (AccountingType.ASSET, AccountingType.PAYABLE),      # I repay friend
        ]
        if (from_acct, to_acct) not in valid_repayments:
            errors.append(
                "LOAN_REPAID: must be Receivable→Asset (friend repays me) "
                "or Asset→Payable (I repay friend)."
            )

    # REIMBURSEMENT_RECEIVED
    elif nature == TransactionNature.REIMBURSEMENT_RECEIVED:
        if to_acct != AccountingType.ASSET:
            errors.append(
                "REIMBURSEMENT_RECEIVED must flow into an ASSET account."
            )


# ─── Prevent invalid account-type movements for non-transfer ───────────────

def _check_no_expense_to_receivable(
    txn: TransactionInput, errors: list[str]
) -> None:
    """Block nonsensical flows like Expense → Receivable."""
    if txn.transaction_type == TransactionType.EXPENSE and txn.to_account_type:
        acct_type = infer_accounting_type(txn.to_account_type)
        if acct_type == AccountingType.RECEIVABLE:
            errors.append("Cannot route an EXPENSE to a RECEIVABLE account.")


# ─── Public API ─────────────────────────────────────────────────────────────

ALL_RULES = [
    _check_amount,
    _check_nature_type_match,
    _check_expense_has_category,
    _check_income_no_from_account,
    _check_transfer_has_both_accounts,
    _check_loan_has_counterparty,
    _check_account_type_movements,
    _check_no_expense_to_receivable,
]


def validate_transaction(txn: TransactionInput) -> list[str]:
    """
    Run all validation rules.  Returns a list of error messages (empty = valid).
    Raises ``ValidationError`` if any rule fails.
    """
    errors: list[str] = []
    for rule in ALL_RULES:
        rule(txn, errors)
    if errors:
        raise ValidationError(errors)
    return errors


def validate_transaction_soft(txn: TransactionInput) -> list[str]:
    """
    Same checks as ``validate_transaction`` but returns errors instead of raising.
    Useful for UI validation before submit.
    """
    errors: list[str] = []
    for rule in ALL_RULES:
        rule(txn, errors)
    return errors


# ─── UX helpers ─────────────────────────────────────────────────────────────

def get_ux_hints(
    txn_type: TransactionType,
    txn_nature: TransactionNature,
) -> dict:
    """
    Return UX-level hints for the frontend form:
      - show_category: bool
      - require_counterparty: bool
      - require_both_accounts: bool
      - affects_net_worth: bool
    """
    is_transfer = txn_type == TransactionType.TRANSFER
    is_loan = txn_nature in {
        TransactionNature.LOAN_GIVEN,
        TransactionNature.LOAN_RECEIVED,
        TransactionNature.LOAN_REPAID,
    }

    # Transfers and loans do NOT affect net worth
    affects_net_worth = txn_type in (TransactionType.INCOME, TransactionType.EXPENSE)

    return {
        "show_category": not is_transfer,
        "require_counterparty": is_loan or txn_nature in {
            TransactionNature.REIMBURSEMENT_PAID,
            TransactionNature.REIMBURSEMENT_RECEIVED,
        },
        "require_both_accounts": is_transfer,
        "affects_net_worth": affects_net_worth,
    }
