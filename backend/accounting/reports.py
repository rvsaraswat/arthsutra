"""
Reporting engine — produces the five mandated financial reports.

All functions accept a SQLAlchemy ``Session`` and a ``user_id``.
They operate on the new accounting-extended Transaction and LedgerEntry
models but fall back gracefully when legacy data lacks the new fields.

Reports:
  1. getCashFlow(start, end)
  2. getIncomeExpenseSummary(start, end)
  3. getBalanceSheet(as_of)
  4. getOutstandingLoans()
  5. getNetWorthTimeline()
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, func, case, extract
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ReportingEngine:
    """
    All methods are class methods so the engine is stateless & testable.
    They import models lazily to avoid circular imports.
    """

    # ── 1. Cash Flow ────────────────────────────────────────────────────

    @staticmethod
    def get_cash_flow(
        db: Session,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Cash flow report — ALL money movements including transfers.

        Returns::
            {
                "period": {"start": ..., "end": ...},
                "inflows": float,       # income + transfer-in
                "outflows": float,      # expense + transfer-out
                "net_cash_flow": float,
                "by_month": [
                    {"month": "2026-01", "inflows": ..., "outflows": ..., "net": ...},
                    ...
                ],
                "by_type": {
                    "income": float,
                    "expense": float,
                    "transfer_in": float,
                    "transfer_out": float,
                },
            }
        """
        from models import Transaction

        base = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted == False,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )

        rows = base.all()

        inflows = 0.0
        outflows = 0.0
        by_type = {"income": 0.0, "expense": 0.0, "transfer_in": 0.0, "transfer_out": 0.0}
        monthly: dict[str, dict[str, float]] = defaultdict(
            lambda: {"inflows": 0.0, "outflows": 0.0}
        )

        for txn in rows:
            month_key = txn.date.strftime("%Y-%m")
            amt = abs(txn.amount)
            txn_type = txn.transaction_type

            if txn_type == "income":
                inflows += amt
                by_type["income"] += amt
                monthly[month_key]["inflows"] += amt
            elif txn_type == "expense":
                outflows += amt
                by_type["expense"] += amt
                monthly[month_key]["outflows"] += amt
            elif txn_type == "transfer":
                # Transfers show movement but not economic impact
                if txn.amount > 0:
                    by_type["transfer_in"] += amt
                    inflows += amt
                    monthly[month_key]["inflows"] += amt
                else:
                    by_type["transfer_out"] += amt
                    outflows += amt
                    monthly[month_key]["outflows"] += amt

        by_month = sorted(
            [
                {
                    "month": m,
                    "inflows": round(v["inflows"], 2),
                    "outflows": round(v["outflows"], 2),
                    "net": round(v["inflows"] - v["outflows"], 2),
                }
                for m, v in monthly.items()
            ],
            key=lambda x: x["month"],
        )

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "inflows": round(inflows, 2),
            "outflows": round(outflows, 2),
            "net_cash_flow": round(inflows - outflows, 2),
            "by_month": by_month,
            "by_type": {k: round(v, 2) for k, v in by_type.items()},
        }

    # ── 2. Income & Expense Summary ────────────────────────────────────

    @staticmethod
    def get_income_expense_summary(
        db: Session,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Income & expense summary — EXCLUDES transfers (they don't affect net worth).

        Returns::
            {
                "total_income": float,
                "total_expenses": float,
                "net": float,
                "savings_rate": float,  # (income - expenses) / income
                "income_breakdown": [{"nature": ..., "total": ...}],
                "expense_breakdown": [{"nature": ..., "category": ..., "total": ...}],
            }
        """
        from models import Transaction

        rows = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.is_deleted == False,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.transaction_type.in_(["income", "expense"]),
            )
            .all()
        )

        total_income = 0.0
        total_expenses = 0.0
        income_by_nature: dict[str, float] = defaultdict(float)
        expense_by_nature: dict[str, float] = defaultdict(float)

        for txn in rows:
            amt = abs(txn.amount)
            nature = getattr(txn, "transaction_nature", None) or "uncategorized"

            if txn.transaction_type == "income":
                total_income += amt
                income_by_nature[nature] += amt
            else:
                total_expenses += amt
                key = txn.merchant_category or nature
                expense_by_nature[key] += amt

        savings_rate = (
            (total_income - total_expenses) / total_income
            if total_income > 0 else 0.0
        )

        return {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net": round(total_income - total_expenses, 2),
            "savings_rate": round(savings_rate * 100, 2),
            "income_breakdown": sorted(
                [{"nature": k, "total": round(v, 2)} for k, v in income_by_nature.items()],
                key=lambda x: x["total"], reverse=True,
            ),
            "expense_breakdown": sorted(
                [{"nature": k, "total": round(v, 2)} for k, v in expense_by_nature.items()],
                key=lambda x: x["total"], reverse=True,
            ),
        }

    # ── 3. Balance Sheet ───────────────────────────────────────────────

    @staticmethod
    def get_balance_sheet(
        db: Session,
        user_id: int,
        as_of: datetime,
    ) -> dict[str, Any]:
        """
        Balance sheet: Assets - Liabilities = Net Worth.

        Includes:
          - Real accounts (bank, wallet, investments)
          - Receivables (loans given, pending)
          - Payables (loans owed)
          - Credit card balances (liability)

        Returns::
            {
                "as_of": str,
                "assets": [{"account_id": ..., "name": ..., "balance": ...}],
                "liabilities": [{"account_id": ..., "name": ..., "balance": ...}],
                "receivables": [{"account_id": ..., "name": ..., "balance": ...}],
                "payables": [{"account_id": ..., "name": ..., "balance": ...}],
                "total_assets": float,
                "total_liabilities": float,
                "net_worth": float,
            }
        """
        from models import Account, Transaction
        from .enums import infer_accounting_type, AccountingType

        # Get all active accounts
        accounts = (
            db.query(Account)
            .filter(Account.user_id == user_id, Account.is_active == True)
            .all()
        )

        # Compute running balance per account from transactions up to as_of
        balances: dict[int, float] = {}
        for acct in accounts:
            txn_sum = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.account_id == acct.id,
                    Transaction.is_deleted == False,
                    Transaction.date <= as_of,
                )
                .scalar()
            ) or 0.0
            balances[acct.id] = float(txn_sum)

        # Classify
        assets = []
        liabilities = []
        receivables = []
        payables = []

        for acct in accounts:
            acct_type = infer_accounting_type(acct.account_type)
            entry = {
                "account_id": acct.id,
                "name": acct.name,
                "account_type": acct.account_type,
                "accounting_type": acct_type.value,
                "balance": round(abs(balances.get(acct.id, 0.0)), 2),
                "currency": acct.currency,
            }
            if acct_type == AccountingType.ASSET:
                assets.append(entry)
            elif acct_type == AccountingType.LIABILITY:
                liabilities.append(entry)
            elif acct_type == AccountingType.RECEIVABLE:
                receivables.append(entry)
            elif acct_type == AccountingType.PAYABLE:
                payables.append(entry)

        total_assets = sum(a["balance"] for a in assets) + sum(r["balance"] for r in receivables)
        total_liabilities = sum(l["balance"] for l in liabilities) + sum(p["balance"] for p in payables)

        return {
            "as_of": as_of.isoformat(),
            "assets": assets,
            "liabilities": liabilities,
            "receivables": receivables,
            "payables": payables,
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "net_worth": round(total_assets - total_liabilities, 2),
        }

    # ── 4. Outstanding Loans ───────────────────────────────────────────

    @staticmethod
    def get_outstanding_loans(
        db: Session,
        user_id: int,
    ) -> dict[str, Any]:
        """
        Summarise all open loans — both given and received.

        Returns::
            {
                "loans_given": [
                    {"account_id": ..., "counterparty": ..., "balance": ..., "currency": ...}
                ],
                "loans_received": [...],
                "total_receivable": float,
                "total_payable": float,
                "net_loan_position": float,  # positive = others owe me more
            }
        """
        from models import Account
        from .enums import infer_accounting_type, AccountingType

        accounts = (
            db.query(Account)
            .filter(Account.user_id == user_id, Account.is_active == True)
            .all()
        )

        loans_given = []
        loans_received = []

        for acct in accounts:
            acct_type = infer_accounting_type(acct.account_type)
            if acct_type == AccountingType.RECEIVABLE and acct.balance != 0:
                loans_given.append({
                    "account_id": acct.id,
                    "counterparty": acct.name,
                    "balance": round(abs(acct.balance), 2),
                    "currency": acct.currency,
                })
            elif acct_type == AccountingType.PAYABLE and acct.balance != 0:
                loans_received.append({
                    "account_id": acct.id,
                    "counterparty": acct.name,
                    "balance": round(abs(acct.balance), 2),
                    "currency": acct.currency,
                })

        total_receivable = sum(l["balance"] for l in loans_given)
        total_payable = sum(l["balance"] for l in loans_received)

        return {
            "loans_given": loans_given,
            "loans_received": loans_received,
            "total_receivable": round(total_receivable, 2),
            "total_payable": round(total_payable, 2),
            "net_loan_position": round(total_receivable - total_payable, 2),
        }

    # ── 5. Net Worth Timeline ──────────────────────────────────────────

    @staticmethod
    def get_net_worth_timeline(
        db: Session,
        user_id: int,
        months: int = 12,
    ) -> dict[str, Any]:
        """
        Monthly net-worth snapshots going back ``months`` months.

        Net worth = sum(asset balances) + sum(receivable) - sum(liability) - sum(payable)

        Computed incrementally from income/expense transactions only
        (transfers cancel out).

        Returns::
            {
                "timeline": [
                    {"month": "2026-01", "net_worth": ..., "income": ..., "expenses": ...},
                    ...
                ]
            }
        """
        from models import Transaction, Account
        from .enums import infer_accounting_type, AccountingType

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 31)

        # Monthly income/expense totals (transfers excluded — they're net-zero)
        rows = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.is_deleted == False,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.transaction_type.in_(["income", "expense"]),
            )
            .all()
        )

        monthly: dict[str, dict[str, float]] = defaultdict(
            lambda: {"income": 0.0, "expenses": 0.0}
        )
        for txn in rows:
            month_key = txn.date.strftime("%Y-%m")
            amt = abs(txn.amount)
            if txn.transaction_type == "income":
                monthly[month_key]["income"] += amt
            else:
                monthly[month_key]["expenses"] += amt

        # Starting net worth from account balances
        accounts = (
            db.query(Account)
            .filter(Account.user_id == user_id, Account.is_active == True)
            .all()
        )
        base_net_worth = 0.0
        for acct in accounts:
            acct_type = infer_accounting_type(acct.account_type)
            if acct_type in (AccountingType.ASSET, AccountingType.RECEIVABLE):
                base_net_worth += acct.balance
            else:
                base_net_worth -= acct.balance

        # Build timeline
        sorted_months = sorted(monthly.keys())
        timeline = []
        running_nw = base_net_worth

        # Adjust: subtract all future changes to get to starting point
        # Then walk forward
        total_delta = sum(
            m["income"] - m["expenses"] for m in monthly.values()
        )
        running_nw -= total_delta  # Go back to start

        for month_key in sorted_months:
            data = monthly[month_key]
            delta = data["income"] - data["expenses"]
            running_nw += delta
            timeline.append({
                "month": month_key,
                "net_worth": round(running_nw, 2),
                "income": round(data["income"], 2),
                "expenses": round(data["expenses"], 2),
            })

        return {"timeline": timeline}
