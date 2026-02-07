"""
Accounting enums — the single source of truth for transaction and account
classification throughout the system.
"""
from enum import Enum


# ─── Transaction Type (top-level movement classification) ───────────────────

class TransactionType(str, Enum):
    """Top-level type: does money enter, leave, or move internally?"""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


# ─── Transaction Nature (semantic intent) ───────────────────────────────────

class TransactionNature(str, Enum):
    """Second dimension — WHY did the money move?"""

    # Income natures
    SALARY = "salary"
    BUSINESS_INCOME = "business_income"
    INVESTMENT_INCOME = "investment_income"
    GIFT_RECEIVED = "gift_received"
    REFUND = "refund"
    OTHER_INCOME = "other_income"

    # Expense natures
    PURCHASE = "purchase"
    SUBSCRIPTION = "subscription"
    BILL_PAYMENT = "bill_payment"
    REIMBURSEMENT_PAID = "reimbursement_paid"        # I repay friend who paid for me
    GIFT_GIVEN = "gift_given"
    OTHER_EXPENSE = "other_expense"

    # Transfer natures (no net-worth impact)
    INTERNAL_TRANSFER = "internal_transfer"           # Own account → own account
    CC_BILL_PAYMENT = "cc_bill_payment"               # Asset → Liability (pay off card)
    REIMBURSEMENT_RECEIVED = "reimbursement_received" # Someone repays me

    # Loan natures (no net-worth impact at origination)
    LOAN_GIVEN = "loan_given"           # I lend money → Asset → Receivable
    LOAN_RECEIVED = "loan_received"     # I borrow → Payable → Asset
    LOAN_REPAID = "loan_repaid"         # Repayment of any loan

    # Catch-all
    ADJUSTMENT = "adjustment"  # Manual balance correction


# ─── Accounting Type (for accounts) ────────────────────────────────────────

class AccountingType(str, Enum):
    """Double-entry account classification."""
    ASSET = "asset"           # bank, cash, wallet, savings, investments
    LIABILITY = "liability"   # credit card, loan payable
    RECEIVABLE = "receivable" # friend/person owes me
    PAYABLE = "payable"       # I owe friend/person


# ─── Mapping: existing account_type → AccountingType ───────────────────────

ACCOUNT_TYPE_TO_ACCOUNTING: dict[str, AccountingType] = {
    # Banking → ASSET
    "savings": AccountingType.ASSET,
    "current": AccountingType.ASSET,
    "salary": AccountingType.ASSET,
    "NRO": AccountingType.ASSET,
    "NRE": AccountingType.ASSET,
    # Credit → LIABILITY
    "credit_card": AccountingType.LIABILITY,
    "overdraft": AccountingType.LIABILITY,
    # Fixed → ASSET
    "FD": AccountingType.ASSET,
    "RD": AccountingType.ASSET,
    # Retirement → ASSET
    "PPF": AccountingType.ASSET,
    "EPF": AccountingType.ASSET,
    "NPS": AccountingType.ASSET,
    # Investments → ASSET
    "stocks": AccountingType.ASSET,
    "mutual_funds": AccountingType.ASSET,
    "bonds": AccountingType.ASSET,
    "crypto": AccountingType.ASSET,
    # Other → ASSET
    "wallet": AccountingType.ASSET,
    "cash": AccountingType.ASSET,
    "other": AccountingType.ASSET,
    # New accounting-specific types
    "receivable": AccountingType.RECEIVABLE,
    "payable": AccountingType.PAYABLE,
}


def infer_accounting_type(account_type: str) -> AccountingType:
    """Derive AccountingType from an existing account_type string."""
    return ACCOUNT_TYPE_TO_ACCOUNTING.get(account_type, AccountingType.ASSET)


# ─── Valid nature → type mappings ──────────────────────────────────────────

VALID_NATURE_FOR_TYPE: dict[TransactionType, set[TransactionNature]] = {
    TransactionType.INCOME: {
        TransactionNature.SALARY,
        TransactionNature.BUSINESS_INCOME,
        TransactionNature.INVESTMENT_INCOME,
        TransactionNature.GIFT_RECEIVED,
        TransactionNature.REFUND,
        TransactionNature.OTHER_INCOME,
    },
    TransactionType.EXPENSE: {
        TransactionNature.PURCHASE,
        TransactionNature.SUBSCRIPTION,
        TransactionNature.BILL_PAYMENT,
        TransactionNature.REIMBURSEMENT_PAID,
        TransactionNature.GIFT_GIVEN,
        TransactionNature.OTHER_EXPENSE,
    },
    TransactionType.TRANSFER: {
        TransactionNature.INTERNAL_TRANSFER,
        TransactionNature.CC_BILL_PAYMENT,
        TransactionNature.REIMBURSEMENT_RECEIVED,
        TransactionNature.LOAN_GIVEN,
        TransactionNature.LOAN_RECEIVED,
        TransactionNature.LOAN_REPAID,
        TransactionNature.ADJUSTMENT,
    },
}


def is_valid_nature_for_type(
    txn_type: TransactionType,
    txn_nature: TransactionNature,
) -> bool:
    """Check that the nature is valid for the given type."""
    allowed = VALID_NATURE_FOR_TYPE.get(txn_type, set())
    return txn_nature in allowed
