"""
AI transaction classifier stub.

This module provides the hook for future ML/LLM-based auto-classification.
Currently uses a rule-based heuristic; the interface is stable so that
a model-based implementation can be swapped in later.

Classification priority:
  1. Intent — "will this money come back?"
  2. Counterparty — who is on the other side
  3. Account types — what accounts are involved
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Optional

from .enums import TransactionNature, TransactionType

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of auto-classification."""
    transaction_type: TransactionType
    transaction_nature: TransactionNature
    confidence: float  # 0.0 – 1.0
    reasoning: str = ""


class TransactionClassifier:
    """
    Classify a raw transaction description into type + nature.

    Current implementation: rule-based keyword matching.
    Future: swap in an LLM or fine-tuned model.
    """

    # ── keyword maps (order matters — first match wins) ────────────

    _NATURE_PATTERNS: list[tuple[str, TransactionType, TransactionNature, float]] = [
        # Loans
        (r"(?i)\bloan\s*(?:to|given|lent)\b", TransactionType.TRANSFER, TransactionNature.LOAN_GIVEN, 0.85),
        (r"(?i)\bloan\s*(?:from|received|borrowed)\b", TransactionType.TRANSFER, TransactionNature.LOAN_RECEIVED, 0.85),
        (r"(?i)\bloan\s*(?:repay|repaid|return)\b", TransactionType.TRANSFER, TransactionNature.LOAN_REPAID, 0.85),

        # Internal transfers
        (r"(?i)\b(?:own\s*account|self)\s*transfer\b", TransactionType.TRANSFER, TransactionNature.INTERNAL_TRANSFER, 0.95),
        (r"(?i)\btransfer\s*(?:from|to)\s*own\b", TransactionType.TRANSFER, TransactionNature.INTERNAL_TRANSFER, 0.90),

        # CC bill
        (r"(?i)\b(?:card|cc)\s*bill\s*pay", TransactionType.TRANSFER, TransactionNature.CC_BILL_PAYMENT, 0.90),
        (r"(?i)\bbill\s*(?:ca\s*rd|card).*paid\b", TransactionType.TRANSFER, TransactionNature.CC_BILL_PAYMENT, 0.85),

        # Reimbursement
        (r"(?i)\breimburs", TransactionType.TRANSFER, TransactionNature.REIMBURSEMENT_RECEIVED, 0.75),

        # Salary
        (r"(?i)\b(?:salary|payroll|wages)\b", TransactionType.INCOME, TransactionNature.SALARY, 0.90),

        # Business income
        (r"(?i)\b(?:invoice|freelance|consulting)\s*(?:pay|receipt|income)\b", TransactionType.INCOME, TransactionNature.BUSINESS_INCOME, 0.80),

        # Subscriptions
        (r"(?i)\b(?:netflix|spotify|amazon\s*prime|youtube\s*premium|disney|subscription)\b", TransactionType.EXPENSE, TransactionNature.SUBSCRIPTION, 0.85),

        # Standing order / auto-debit → likely bill
        (r"(?i)\b(?:standing\s*order|auto\s*debit|direct\s*debit)\b", TransactionType.EXPENSE, TransactionNature.BILL_PAYMENT, 0.70),
    ]

    def classify(
        self,
        description: str,
        amount: float = 0.0,
        from_account_type: Optional[str] = None,
        to_account_type: Optional[str] = None,
    ) -> ClassificationResult:
        """
        Classify a transaction from its description and context.

        Args:
            description: Raw transaction description text.
            amount: Transaction amount (positive = credit, negative = debit).
            from_account_type: Source account type string (optional).
            to_account_type: Destination account type string (optional).

        Returns:
            ClassificationResult with type, nature, and confidence.
        """
        desc_upper = (description or "").upper()

        # 1. Try pattern-based classification
        for pattern, txn_type, txn_nature, confidence in self._NATURE_PATTERNS:
            if re.search(pattern, description):
                return ClassificationResult(
                    transaction_type=txn_type,
                    transaction_nature=txn_nature,
                    confidence=confidence,
                    reasoning=f"Matched pattern: {pattern}",
                )

        # 2. Account-type heuristic
        if from_account_type and to_account_type:
            result = self._classify_by_accounts(
                from_account_type, to_account_type, description
            )
            if result:
                return result

        # 3. Sign-based fallback
        if amount > 0:
            return ClassificationResult(
                transaction_type=TransactionType.INCOME,
                transaction_nature=TransactionNature.OTHER_INCOME,
                confidence=0.30,
                reasoning="Fallback: positive amount → income",
            )
        else:
            return ClassificationResult(
                transaction_type=TransactionType.EXPENSE,
                transaction_nature=TransactionNature.PURCHASE,
                confidence=0.30,
                reasoning="Fallback: negative amount → expense",
            )

    def _classify_by_accounts(
        self,
        from_type: str,
        to_type: str,
        description: str,
    ) -> Optional[ClassificationResult]:
        """Infer type/nature from account types involved."""
        from .enums import infer_accounting_type, AccountingType

        from_acct = infer_accounting_type(from_type)
        to_acct = infer_accounting_type(to_type)

        # Asset → Asset = internal transfer
        if from_acct == AccountingType.ASSET and to_acct == AccountingType.ASSET:
            return ClassificationResult(
                transaction_type=TransactionType.TRANSFER,
                transaction_nature=TransactionNature.INTERNAL_TRANSFER,
                confidence=0.80,
                reasoning="Both accounts are ASSET → internal transfer",
            )

        # Asset → LIABILITY = CC bill or loan repayment
        if from_acct == AccountingType.ASSET and to_acct == AccountingType.LIABILITY:
            return ClassificationResult(
                transaction_type=TransactionType.TRANSFER,
                transaction_nature=TransactionNature.CC_BILL_PAYMENT,
                confidence=0.75,
                reasoning="ASSET → LIABILITY → CC bill payment",
            )

        # Asset → Receivable = loan given
        if from_acct == AccountingType.ASSET and to_acct == AccountingType.RECEIVABLE:
            return ClassificationResult(
                transaction_type=TransactionType.TRANSFER,
                transaction_nature=TransactionNature.LOAN_GIVEN,
                confidence=0.80,
                reasoning="ASSET → RECEIVABLE → loan given",
            )

        # Payable → Asset = loan received
        if from_acct == AccountingType.PAYABLE and to_acct == AccountingType.ASSET:
            return ClassificationResult(
                transaction_type=TransactionType.TRANSFER,
                transaction_nature=TransactionNature.LOAN_RECEIVED,
                confidence=0.80,
                reasoning="PAYABLE → ASSET → loan received",
            )

        # Receivable → Asset = loan repaid (friend pays back)
        if from_acct == AccountingType.RECEIVABLE and to_acct == AccountingType.ASSET:
            return ClassificationResult(
                transaction_type=TransactionType.TRANSFER,
                transaction_nature=TransactionNature.LOAN_REPAID,
                confidence=0.80,
                reasoning="RECEIVABLE → ASSET → loan repaid by counterparty",
            )

        # Asset → Payable = I repay loan
        if from_acct == AccountingType.ASSET and to_acct == AccountingType.PAYABLE:
            return ClassificationResult(
                transaction_type=TransactionType.TRANSFER,
                transaction_nature=TransactionNature.LOAN_REPAID,
                confidence=0.80,
                reasoning="ASSET → PAYABLE → I repay my loan",
            )

        return None

    # ── Future: LLM-based classification ───────────────────────────

    async def classify_with_llm(
        self,
        description: str,
        amount: float,
        context: Optional[dict] = None,
    ) -> ClassificationResult:
        """
        Placeholder for LLM-based classification.

        Will call Ollama/OpenAI with a structured prompt to infer:
          - Intent: "will this money come back?"
          - Counterparty classification
          - Nature inference

        TODO: Implement when Ollama integration is ready.
        """
        logger.info("LLM classification not yet implemented, falling back to rules")
        return self.classify(description, amount)
