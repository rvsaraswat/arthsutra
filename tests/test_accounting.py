"""
Unit tests for accounting correctness.

Tests cover:
  1. Validation rules (all mandatory accounting rules)
  2. Double-entry ledger balance
  3. AI classifier
  4. Enum consistency

Run:  python -m pytest tests/test_accounting.py -v
"""
import sys
import os
import pytest
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from accounting.enums import (
    AccountingType,
    TransactionNature,
    TransactionType,
    infer_accounting_type,
    is_valid_nature_for_type,
    VALID_NATURE_FOR_TYPE,
)
from accounting.validation import (
    TransactionInput,
    ValidationError,
    validate_transaction,
    validate_transaction_soft,
    get_ux_hints,
)
from accounting.ledger import LedgerEngine
from accounting.classifier import TransactionClassifier


# ═══════════════════════════════════════════════════════════════════════════
#  ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestEnums:
    def test_transaction_types_complete(self):
        assert set(TransactionType) == {
            TransactionType.INCOME,
            TransactionType.EXPENSE,
            TransactionType.TRANSFER,
        }

    def test_every_nature_belongs_to_exactly_one_type(self):
        """Each nature must be in exactly one type bucket."""
        all_natures = set()
        for natures in VALID_NATURE_FOR_TYPE.values():
            for n in natures:
                assert n not in all_natures, f"{n} appears in multiple types"
                all_natures.add(n)
        # Every defined nature should be accounted for
        for n in TransactionNature:
            assert n in all_natures, f"{n} not assigned to any type"

    def test_account_type_mapping(self):
        assert infer_accounting_type("savings") == AccountingType.ASSET
        assert infer_accounting_type("credit_card") == AccountingType.LIABILITY
        assert infer_accounting_type("receivable") == AccountingType.RECEIVABLE
        assert infer_accounting_type("payable") == AccountingType.PAYABLE
        assert infer_accounting_type("overdraft") == AccountingType.LIABILITY
        assert infer_accounting_type("unknown_type") == AccountingType.ASSET  # default

    def test_valid_nature_for_type(self):
        assert is_valid_nature_for_type(TransactionType.INCOME, TransactionNature.SALARY)
        assert is_valid_nature_for_type(TransactionType.EXPENSE, TransactionNature.PURCHASE)
        assert is_valid_nature_for_type(TransactionType.TRANSFER, TransactionNature.INTERNAL_TRANSFER)
        assert not is_valid_nature_for_type(TransactionType.INCOME, TransactionNature.PURCHASE)
        assert not is_valid_nature_for_type(TransactionType.EXPENSE, TransactionNature.SALARY)
        assert not is_valid_nature_for_type(TransactionType.TRANSFER, TransactionNature.SALARY)


# ═══════════════════════════════════════════════════════════════════════════
#  VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestValidation:

    def test_valid_income(self):
        """Income with category and no from_account should pass."""
        txn = TransactionInput(
            transaction_type=TransactionType.INCOME,
            transaction_nature=TransactionNature.SALARY,
            amount=50000,
            to_account_id=1,
            category="Salary",
        )
        errors = validate_transaction_soft(txn)
        assert errors == []

    def test_expense_without_category_fails(self):
        """EXPENSE requires a category."""
        txn = TransactionInput(
            transaction_type=TransactionType.EXPENSE,
            transaction_nature=TransactionNature.PURCHASE,
            amount=500,
            from_account_id=1,
            # No category
        )
        errors = validate_transaction_soft(txn)
        assert any("category" in e.lower() for e in errors)

    def test_expense_with_category_passes(self):
        txn = TransactionInput(
            transaction_type=TransactionType.EXPENSE,
            transaction_nature=TransactionNature.PURCHASE,
            amount=500,
            from_account_id=1,
            category="Groceries",
        )
        errors = validate_transaction_soft(txn)
        assert errors == []

    def test_income_with_from_account_fails(self):
        """INCOME must not have a from_account."""
        txn = TransactionInput(
            transaction_type=TransactionType.INCOME,
            transaction_nature=TransactionNature.SALARY,
            amount=50000,
            from_account_id=1,
            to_account_id=2,
            category="Salary",
        )
        errors = validate_transaction_soft(txn)
        assert any("from_account" in e.lower() for e in errors)

    def test_transfer_without_both_accounts_fails(self):
        """TRANSFER requires both from and to accounts."""
        txn = TransactionInput(
            transaction_type=TransactionType.TRANSFER,
            transaction_nature=TransactionNature.INTERNAL_TRANSFER,
            amount=10000,
            from_account_id=1,
            # Missing to_account_id
        )
        errors = validate_transaction_soft(txn)
        assert any("both" in e.lower() or "to_account" in e.lower() for e in errors)

    def test_transfer_with_both_accounts_passes(self):
        txn = TransactionInput(
            transaction_type=TransactionType.TRANSFER,
            transaction_nature=TransactionNature.INTERNAL_TRANSFER,
            amount=10000,
            from_account_id=1,
            to_account_id=2,
            from_account_type="savings",
            to_account_type="current",
        )
        errors = validate_transaction_soft(txn)
        assert errors == []

    def test_negative_amount_fails(self):
        txn = TransactionInput(
            transaction_type=TransactionType.EXPENSE,
            transaction_nature=TransactionNature.PURCHASE,
            amount=-100,
            category="Food",
        )
        errors = validate_transaction_soft(txn)
        assert any("positive" in e.lower() for e in errors)

    def test_wrong_nature_for_type_fails(self):
        """Salary is INCOME nature, not EXPENSE."""
        txn = TransactionInput(
            transaction_type=TransactionType.EXPENSE,
            transaction_nature=TransactionNature.SALARY,
            amount=500,
            category="Food",
        )
        errors = validate_transaction_soft(txn)
        assert any("nature" in e.lower() for e in errors)

    def test_loan_without_counterparty_fails(self):
        txn = TransactionInput(
            transaction_type=TransactionType.TRANSFER,
            transaction_nature=TransactionNature.LOAN_GIVEN,
            amount=5000,
            from_account_id=1,
            to_account_id=2,
            from_account_type="savings",
            to_account_type="receivable",
            # No counterparty
        )
        errors = validate_transaction_soft(txn)
        assert any("counterparty" in e.lower() for e in errors)

    def test_loan_with_counterparty_passes(self):
        txn = TransactionInput(
            transaction_type=TransactionType.TRANSFER,
            transaction_nature=TransactionNature.LOAN_GIVEN,
            amount=5000,
            from_account_id=1,
            to_account_id=2,
            from_account_type="savings",
            to_account_type="receivable",
            counterparty="John",
        )
        errors = validate_transaction_soft(txn)
        assert errors == []

    def test_internal_transfer_must_be_asset_to_asset(self):
        txn = TransactionInput(
            transaction_type=TransactionType.TRANSFER,
            transaction_nature=TransactionNature.INTERNAL_TRANSFER,
            amount=10000,
            from_account_id=1,
            to_account_id=2,
            from_account_type="savings",
            to_account_type="credit_card",  # LIABILITY, not ASSET
        )
        errors = validate_transaction_soft(txn)
        assert any("asset" in e.lower() for e in errors)

    def test_cc_bill_must_be_asset_to_liability(self):
        txn = TransactionInput(
            transaction_type=TransactionType.TRANSFER,
            transaction_nature=TransactionNature.CC_BILL_PAYMENT,
            amount=15000,
            from_account_id=1,
            to_account_id=2,
            from_account_type="savings",
            to_account_type="credit_card",
        )
        errors = validate_transaction_soft(txn)
        assert errors == []

    def test_loan_given_must_be_asset_to_receivable(self):
        txn = TransactionInput(
            transaction_type=TransactionType.TRANSFER,
            transaction_nature=TransactionNature.LOAN_GIVEN,
            amount=5000,
            from_account_id=1,
            to_account_id=2,
            from_account_type="savings",
            to_account_type="savings",  # Should be receivable
            counterparty="John",
        )
        errors = validate_transaction_soft(txn)
        assert any("receivable" in e.lower() for e in errors)

    def test_expense_to_receivable_blocked(self):
        txn = TransactionInput(
            transaction_type=TransactionType.EXPENSE,
            transaction_nature=TransactionNature.PURCHASE,
            amount=500,
            category="Food",
            to_account_type="receivable",
        )
        errors = validate_transaction_soft(txn)
        assert any("receivable" in e.lower() for e in errors)

    def test_validate_raises_on_error(self):
        txn = TransactionInput(
            transaction_type=TransactionType.EXPENSE,
            transaction_nature=TransactionNature.PURCHASE,
            amount=-1,
        )
        with pytest.raises(ValidationError) as exc_info:
            validate_transaction(txn)
        assert len(exc_info.value.errors) > 0


# ═══════════════════════════════════════════════════════════════════════════
#  LEDGER TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestLedger:
    engine = LedgerEngine()
    now = datetime.utcnow()

    def test_income_entries_balanced(self):
        entries = self.engine.create_entries(
            transaction_id=1,
            txn_type=TransactionType.INCOME,
            txn_nature=TransactionNature.SALARY,
            amount=50000,
            date=self.now,
            to_account_id=1,
            to_account_type="savings",
        )
        assert len(entries) == 2
        total_debit = sum(e.debit for e in entries)
        total_credit = sum(e.credit for e in entries)
        assert abs(total_debit - total_credit) < 0.001

    def test_expense_entries_balanced(self):
        entries = self.engine.create_entries(
            transaction_id=2,
            txn_type=TransactionType.EXPENSE,
            txn_nature=TransactionNature.PURCHASE,
            amount=500,
            date=self.now,
            from_account_id=1,
            from_account_type="savings",
        )
        assert len(entries) == 2
        total_debit = sum(e.debit for e in entries)
        total_credit = sum(e.credit for e in entries)
        assert abs(total_debit - total_credit) < 0.001

    def test_internal_transfer_balanced(self):
        entries = self.engine.create_entries(
            transaction_id=3,
            txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.INTERNAL_TRANSFER,
            amount=10000,
            date=self.now,
            from_account_id=1,
            from_account_type="savings",
            to_account_id=2,
            to_account_type="current",
        )
        assert len(entries) == 2
        total_debit = sum(e.debit for e in entries)
        total_credit = sum(e.credit for e in entries)
        assert abs(total_debit - total_credit) < 0.001

    def test_internal_transfer_debits_credits_correct(self):
        """
        Savings → Current:
          - Savings (ASSET) decreases → Credit
          - Current (ASSET) increases → Debit
        """
        entries = self.engine.create_entries(
            transaction_id=4,
            txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.INTERNAL_TRANSFER,
            amount=5000,
            date=self.now,
            from_account_id=1,
            from_account_type="savings",
            to_account_id=2,
            to_account_type="current",
        )
        from_entry = [e for e in entries if e.account_id == 1][0]
        to_entry = [e for e in entries if e.account_id == 2][0]
        # Source asset decreases → credit
        assert from_entry.credit == 5000
        assert from_entry.debit == 0
        # Destination asset increases → debit
        assert to_entry.debit == 5000
        assert to_entry.credit == 0

    def test_loan_given_entries(self):
        """
        Lending money: Savings (ASSET) → Friend (RECEIVABLE)
        Asset decreases → Credit
        Receivable increases → Debit
        """
        entries = self.engine.create_entries(
            transaction_id=5,
            txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.LOAN_GIVEN,
            amount=3000,
            date=self.now,
            from_account_id=1,
            from_account_type="savings",
            to_account_id=10,
            to_account_type="receivable",
        )
        assert len(entries) == 2
        from_entry = [e for e in entries if e.account_id == 1][0]
        to_entry = [e for e in entries if e.account_id == 10][0]
        assert from_entry.credit == 3000  # Asset decreases
        assert to_entry.debit == 3000     # Receivable increases

    def test_loan_repaid_entries(self):
        """
        Friend repays: Friend (RECEIVABLE) → Savings (ASSET)
        Receivable decreases → Credit
        Asset increases → Debit
        """
        entries = self.engine.create_entries(
            transaction_id=6,
            txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.LOAN_REPAID,
            amount=3000,
            date=self.now,
            from_account_id=10,
            from_account_type="receivable",
            to_account_id=1,
            to_account_type="savings",
        )
        from_entry = [e for e in entries if e.account_id == 10][0]
        to_entry = [e for e in entries if e.account_id == 1][0]
        assert from_entry.credit == 3000  # Receivable decreases
        assert to_entry.debit == 3000     # Asset increases

    def test_cc_bill_payment_entries(self):
        """
        Pay CC: Savings (ASSET) → Credit Card (LIABILITY)
        Asset decreases → Credit
        Liability decreases → Debit  (paying off debt)
        """
        entries = self.engine.create_entries(
            transaction_id=7,
            txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.CC_BILL_PAYMENT,
            amount=15000,
            date=self.now,
            from_account_id=1,
            from_account_type="savings",
            to_account_id=3,
            to_account_type="credit_card",
        )
        from_entry = [e for e in entries if e.account_id == 1][0]
        to_entry = [e for e in entries if e.account_id == 3][0]
        assert from_entry.credit == 15000  # Asset decreases
        assert to_entry.debit == 15000     # Liability decreases (paid off)

    def test_loan_received_entries(self):
        """
        I borrow money: Payable → Savings (ASSET)
        Payable increases → Credit  (new debt)
        Asset increases → Debit     (got cash)
        """
        entries = self.engine.create_entries(
            transaction_id=8,
            txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.LOAN_RECEIVED,
            amount=10000,
            date=self.now,
            from_account_id=20,
            from_account_type="payable",
            to_account_id=1,
            to_account_type="savings",
        )
        from_entry = [e for e in entries if e.account_id == 20][0]
        to_entry = [e for e in entries if e.account_id == 1][0]
        assert from_entry.credit == 10000  # Payable increases (new debt)
        assert to_entry.debit == 10000     # Asset increases (got cash)

    def test_i_repay_loan_entries(self):
        """
        I repay: Savings (ASSET) → Payable
        Asset decreases → Credit
        Payable decreases → Debit
        """
        entries = self.engine.create_entries(
            transaction_id=9,
            txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.LOAN_REPAID,
            amount=10000,
            date=self.now,
            from_account_id=1,
            from_account_type="savings",
            to_account_id=20,
            to_account_type="payable",
        )
        from_entry = [e for e in entries if e.account_id == 1][0]
        to_entry = [e for e in entries if e.account_id == 20][0]
        assert from_entry.credit == 10000  # Asset decreases
        assert to_entry.debit == 10000     # Payable decreases (debt reduced)

    def test_account_balance_computation(self):
        """Test balance calculation from ledger entries."""
        entries = self.engine.create_entries(
            transaction_id=10,
            txn_type=TransactionType.INCOME,
            txn_nature=TransactionNature.SALARY,
            amount=50000,
            date=self.now,
            to_account_id=1,
            to_account_type="savings",
        )
        balance = LedgerEngine.account_balance_from_entries(
            entries, account_id=1, acct_type=AccountingType.ASSET
        )
        assert balance == 50000  # Salary credit to asset → balance increases


# ═══════════════════════════════════════════════════════════════════════════
#  CLASSIFIER TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestClassifier:
    classifier = TransactionClassifier()

    def test_salary_detection(self):
        result = self.classifier.classify("Monthly Salary Credit")
        assert result.transaction_type == TransactionType.INCOME
        assert result.transaction_nature == TransactionNature.SALARY
        assert result.confidence >= 0.8

    def test_own_account_transfer_detection(self):
        result = self.classifier.classify("OWN ACCOUNT TRANSFER FROM SAVINGS")
        assert result.transaction_type == TransactionType.TRANSFER
        assert result.transaction_nature == TransactionNature.INTERNAL_TRANSFER

    def test_cc_bill_detection(self):
        result = self.classifier.classify("CARD BILL PAYMENT,300126K03133,CA RD NO 3633")
        assert result.transaction_type == TransactionType.TRANSFER
        assert result.transaction_nature == TransactionNature.CC_BILL_PAYMENT

    def test_loan_given_detection(self):
        result = self.classifier.classify("Loan to Rahul for trip expenses")
        assert result.transaction_type == TransactionType.TRANSFER
        assert result.transaction_nature == TransactionNature.LOAN_GIVEN

    def test_subscription_detection(self):
        result = self.classifier.classify("Netflix Monthly Subscription")
        assert result.transaction_type == TransactionType.EXPENSE
        assert result.transaction_nature == TransactionNature.SUBSCRIPTION

    def test_account_based_classification(self):
        """When both accounts are ASSET → internal transfer."""
        result = self.classifier.classify(
            "Transfer between accounts",
            from_account_type="savings",
            to_account_type="current",
        )
        assert result.transaction_type == TransactionType.TRANSFER
        assert result.transaction_nature == TransactionNature.INTERNAL_TRANSFER

    def test_asset_to_receivable_classification(self):
        """Asset → Receivable = loan given."""
        result = self.classifier.classify(
            "Sent money to friend",
            from_account_type="savings",
            to_account_type="receivable",
        )
        assert result.transaction_type == TransactionType.TRANSFER
        assert result.transaction_nature == TransactionNature.LOAN_GIVEN

    def test_fallback_positive_amount(self):
        result = self.classifier.classify("Unknown Credit", amount=1500)
        assert result.transaction_type == TransactionType.INCOME
        assert result.confidence < 0.5  # Low confidence fallback

    def test_fallback_negative_amount(self):
        result = self.classifier.classify("Unknown Debit", amount=-500)
        assert result.transaction_type == TransactionType.EXPENSE
        assert result.confidence < 0.5


# ═══════════════════════════════════════════════════════════════════════════
#  UX HINTS TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestUXHints:
    def test_transfer_hides_category(self):
        hints = get_ux_hints(TransactionType.TRANSFER, TransactionNature.INTERNAL_TRANSFER)
        assert hints["show_category"] is False
        assert hints["require_both_accounts"] is True
        assert hints["affects_net_worth"] is False

    def test_expense_shows_category(self):
        hints = get_ux_hints(TransactionType.EXPENSE, TransactionNature.PURCHASE)
        assert hints["show_category"] is True
        assert hints["affects_net_worth"] is True

    def test_loan_requires_counterparty(self):
        hints = get_ux_hints(TransactionType.TRANSFER, TransactionNature.LOAN_GIVEN)
        assert hints["require_counterparty"] is True
        assert hints["affects_net_worth"] is False

    def test_income_affects_net_worth(self):
        hints = get_ux_hints(TransactionType.INCOME, TransactionNature.SALARY)
        assert hints["affects_net_worth"] is True
        assert hints["show_category"] is True  # Income shows category (only TRANSFER hides it)


# ═══════════════════════════════════════════════════════════════════════════
#  SCENARIO TESTS (Full accounting workflow)
# ═══════════════════════════════════════════════════════════════════════════


class TestScenarios:
    engine = LedgerEngine()
    now = datetime.utcnow()

    def test_scenario_salary_then_expense(self):
        """
        1. Receive salary of 50000 into savings
        2. Spend 500 on groceries
        Net worth should be 49500
        """
        all_entries = []

        # Salary
        entries1 = self.engine.create_entries(
            transaction_id=100, txn_type=TransactionType.INCOME,
            txn_nature=TransactionNature.SALARY, amount=50000,
            date=self.now, to_account_id=1, to_account_type="savings",
        )
        all_entries.extend(entries1)

        # Expense
        entries2 = self.engine.create_entries(
            transaction_id=101, txn_type=TransactionType.EXPENSE,
            txn_nature=TransactionNature.PURCHASE, amount=500,
            date=self.now, from_account_id=1, from_account_type="savings",
        )
        all_entries.extend(entries2)

        balance = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=1, acct_type=AccountingType.ASSET
        )
        assert balance == 49500

    def test_scenario_transfer_does_not_change_net_worth(self):
        """
        1. Start with 50000 in savings
        2. Transfer 20000 to current
        Combined net worth should still be 50000
        """
        all_entries = []

        # Initial salary
        entries1 = self.engine.create_entries(
            transaction_id=200, txn_type=TransactionType.INCOME,
            txn_nature=TransactionNature.SALARY, amount=50000,
            date=self.now, to_account_id=1, to_account_type="savings",
        )
        all_entries.extend(entries1)

        # Transfer savings → current
        entries2 = self.engine.create_entries(
            transaction_id=201, txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.INTERNAL_TRANSFER, amount=20000,
            date=self.now,
            from_account_id=1, from_account_type="savings",
            to_account_id=2, to_account_type="current",
        )
        all_entries.extend(entries2)

        savings_balance = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=1, acct_type=AccountingType.ASSET
        )
        current_balance = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=2, acct_type=AccountingType.ASSET
        )

        assert savings_balance == 30000
        assert current_balance == 20000
        assert savings_balance + current_balance == 50000  # Net worth unchanged

    def test_scenario_loan_does_not_change_net_worth(self):
        """
        1. Have 50000 in savings
        2. Lend 5000 to friend (Asset → Receivable)
        3. Net worth: 45000 (savings) + 5000 (receivable) = 50000
        """
        all_entries = []

        entries1 = self.engine.create_entries(
            transaction_id=300, txn_type=TransactionType.INCOME,
            txn_nature=TransactionNature.SALARY, amount=50000,
            date=self.now, to_account_id=1, to_account_type="savings",
        )
        all_entries.extend(entries1)

        entries2 = self.engine.create_entries(
            transaction_id=301, txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.LOAN_GIVEN, amount=5000,
            date=self.now,
            from_account_id=1, from_account_type="savings",
            to_account_id=10, to_account_type="receivable",
        )
        all_entries.extend(entries2)

        savings = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=1, acct_type=AccountingType.ASSET
        )
        receivable = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=10, acct_type=AccountingType.RECEIVABLE
        )

        assert savings == 45000
        assert receivable == 5000
        assert savings + receivable == 50000

    def test_scenario_borrow_and_repay(self):
        """
        1. Borrow 10000 (Payable → Asset) — net worth = 0 (10k assets, 10k liability)
        2. Repay 10000 (Asset → Payable) — net worth = 0 (0 assets, 0 liability)
        """
        all_entries = []

        # Borrow
        entries1 = self.engine.create_entries(
            transaction_id=400, txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.LOAN_RECEIVED, amount=10000,
            date=self.now,
            from_account_id=20, from_account_type="payable",
            to_account_id=1, to_account_type="savings",
        )
        all_entries.extend(entries1)

        savings = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=1, acct_type=AccountingType.ASSET
        )
        payable = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=20, acct_type=AccountingType.PAYABLE
        )
        assert savings == 10000
        assert payable == 10000
        net_worth_after_borrow = savings - payable
        assert net_worth_after_borrow == 0

        # Repay
        entries2 = self.engine.create_entries(
            transaction_id=401, txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.LOAN_REPAID, amount=10000,
            date=self.now,
            from_account_id=1, from_account_type="savings",
            to_account_id=20, to_account_type="payable",
        )
        all_entries.extend(entries2)

        savings = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=1, acct_type=AccountingType.ASSET
        )
        payable = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=20, acct_type=AccountingType.PAYABLE
        )
        assert savings == 0
        assert payable == 0
        assert savings - payable == 0

    def test_scenario_cc_spend_and_payment(self):
        """
        1. Receive salary 50000
        2. Spend 5000 on CC (expense debits CC liability)
           → For simplicity, expense from savings for now
        3. Pay CC bill: Savings → Credit Card (Asset → Liability)
        """
        all_entries = []

        # Salary
        entries1 = self.engine.create_entries(
            transaction_id=500, txn_type=TransactionType.INCOME,
            txn_nature=TransactionNature.SALARY, amount=50000,
            date=self.now, to_account_id=1, to_account_type="savings",
        )
        all_entries.extend(entries1)

        # CC bill payment (15000)
        entries2 = self.engine.create_entries(
            transaction_id=501, txn_type=TransactionType.TRANSFER,
            txn_nature=TransactionNature.CC_BILL_PAYMENT, amount=15000,
            date=self.now,
            from_account_id=1, from_account_type="savings",
            to_account_id=3, to_account_type="credit_card",
        )
        all_entries.extend(entries2)

        savings = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=1, acct_type=AccountingType.ASSET
        )
        cc = LedgerEngine.account_balance_from_entries(
            all_entries, account_id=3, acct_type=AccountingType.LIABILITY
        )

        assert savings == 35000  # 50000 - 15000
        # CC liability decreased (payment made)
        # Since we only have the bill payment entry, CC shows -15000
        # (it was decreased, which for a liability means less owed)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
