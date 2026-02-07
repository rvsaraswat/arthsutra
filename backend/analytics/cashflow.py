"""
Cash-flow analysis engine for Personal Finance Manager.
Calculates income, expenses, and cash-flow metrics.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal
import logging
import pandas as pd

from models import Transaction, get_session

logger = logging.getLogger(__name__)


class CashFlowAnalyzer:
    """Analyze cash-flow patterns and trends."""

    def __init__(self, user_id: int):
        """Initialize cash-flow analyzer for a user."""
        self.user_id = user_id

    def get_monthly_cashflow(
        self,
        year: int,
        month: int,
        session
    ) -> Dict:
        """Get cash-flow for a specific month."""
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

        transactions = session.query(Transaction).filter(
            Transaction.user_id == self.user_id,
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()

        income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')

        return {
            'period': f"{year}-{month:02d}",
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'income': income,
            'expenses': expenses,
            'net_cashflow': income - expenses,
            'savings_rate': round((income - expenses) / income * 100, 2) if income > 0 else 0,
            'transaction_count': len(transactions)
        }

    def get_yearly_cashflow(
        self,
        year: int,
        session
    ) -> Dict:
        """Get cash-flow for a specific year."""
        start_date = datetime(year, 1, 1)
        end_date = datetime(year + 1, 1, 1)

        transactions = session.query(Transaction).filter(
            Transaction.user_id == self.user_id,
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()

        income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')

        return {
            'year': year,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'income': income,
            'expenses': expenses,
            'net_cashflow': income - expenses,
            'savings_rate': round((income - expenses) / income * 100, 2) if income > 0 else 0,
            'transaction_count': len(transactions)
        }

    def get_cashflow_trend(
        self,
        months: int = 12,
        session
    ) -> List[Dict]:
        """Get cash-flow trend over time."""
        trend = []
        end_date = datetime.now()

        for i in range(months):
            start_date = end_date - timedelta(days=30 * i)
            month = start_date.month
            year = start_date.year

            if i == 0:  # Current month
                start_date = datetime(year, month, 1)
                end_date = datetime.now()
            else:
                start_date = datetime(year, month, 1)
                end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

            transactions = session.query(Transaction).filter(
                Transaction.user_id == self.user_id,
                Transaction.date >= start_date,
                Transaction.date < end_date
            ).all()

            income = sum(t.amount for t in transactions if t.transaction_type == 'income')
            expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')

            trend.append({
                'period': f"{year}-{month:02d}",
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'income': income,
                'expenses': expenses,
                'net_cashflow': income - expenses,
                'savings_rate': round((income - expenses) / income * 100, 2) if income > 0 else 0
            })

        return trend

    def get_category_breakdown(
        self,
        start_date: datetime,
        end_date: datetime,
        session
    ) -> Dict:
        """Get expense breakdown by category."""
        transactions = session.query(Transaction).filter(
            Transaction.user_id == self.user_id,
            Transaction.transaction_type == 'expense',
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).all()

        # Group by category
        category_totals = {}
        for t in transactions:
            category = t.category.name if t.category else 'Uncategorized'
            category_totals[category] = category_totals.get(category, 0) + t.amount

        # Sort by amount
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

        return {
            'total_expenses': sum(category_totals.values()),
            'breakdown': [
                {'category': cat, 'amount': amount, 'percentage': round(amount / sum(category_totals.values()) * 100, 2)}
                for cat, amount in sorted_categories
            ]
        }

    def get_cashflow_summary(
        self,
        days: int = 30,
        session
    ) -> Dict:
        """Get comprehensive cash-flow summary."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        transactions = session.query(Transaction).filter(
            Transaction.user_id == self.user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).all()

        income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')
        net_cashflow = income - expenses

        # Calculate daily averages
        daily_transactions = [t for t in transactions if t.date.date() == end_date.date()]
        daily_income = sum(t.amount for t in daily_transactions if t.transaction_type == 'income')
        daily_expenses = sum(t.amount for t in daily_transactions if t.transaction_type == 'expense')

        return {
            'period': f"Last {days} days",
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_income': income,
            'total_expenses': expenses,
            'net_cashflow': net_cashflow,
            'savings_rate': round(net_cashflow / income * 100, 2) if income > 0 else 0,
            'daily_average_income': round(income / days, 2),
            'daily_average_expenses': round(expenses / days, 2),
            'daily_average_savings': round(net_cashflow / days, 2),
            'transaction_count': len(transactions),
            'last_transaction_date': max(t.date for t in transactions).isoformat() if transactions else None
        }

    def detect_spikes(
        self,
        months: int = 6,
        threshold: float = 1.5,
        session
    ) -> List[Dict]:
        """Detect expense spikes compared to average."""
        trend = self.get_cashflow_trend(months, session)
        expenses = [t['expenses'] for t in trend]
        avg_expense = sum(expenses) / len(expenses)

        spikes = []
        for t in trend:
            if t['expenses'] > avg_expense * threshold:
                spikes.append({
                    'period': t['period'],
                    'expenses': t['expenses'],
                    'average_expense': avg_expense,
                    'percentage_above_average': round((t['expenses'] - avg_expense) / avg_expense * 100, 2)
                })

        return spikes

    def get_cashflow_forecast(
        self,
        months: int = 6,
        session
    ) -> List[Dict]:
        """Simple cash-flow forecast based on historical averages."""
        trend = self.get_cashflow_trend(months, session)
        income_avg = sum(t['income'] for t in trend) / len(trend)
        expense_avg = sum(t['expenses'] for t in trend) / len(trend)

        forecast = []
        current_date = datetime.now()

        for i in range(1, months + 1):
            forecast_date = current_date.replace(day=1) + timedelta(days=30 * i)
            year = forecast_date.year
            month = forecast_date.month

            forecast.append({
                'period': f"{year}-{month:02d}",
                'forecasted_income': round(income_avg, 2),
                'forecasted_expenses': round(expense_avg, 2),
                'forecasted_net': round(income_avg - expense_avg, 2)
            })

        return forecast