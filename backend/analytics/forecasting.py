"""
Financial forecasting models using Prophet and statistical methods.
Provides expense forecasting, savings trajectory, and retirement simulation.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import pandas as pd
import numpy as np
from prophet import Prophet

from ..models import Transaction, get_session

logger = logging.getLogger(__name__)


class ExpenseForecaster:
    """Forecast future expenses using Prophet."""

    def __init__(self, model_path: str = None):
        """Initialize expense forecaster."""
        self.model_path = model_path
        self.model = None

    def train(self, transactions: List[Transaction]):
        """
        Train Prophet model on transaction data.

        Args:
            transactions: List of expense transactions
        """
        try:
            # Prepare data for Prophet
            df = pd.DataFrame([
                {
                    'ds': tx.date,
                    'y': tx.amount,
                    'description': tx.description
                }
                for tx in transactions if tx.transaction_type == 'expense'
            ])

            if len(df) < 10:
                logger.warning("Not enough data for forecasting")
                return False

            # Create Prophet model
            self.model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False,
                changepoint_prior_scale=0.05
            )

            # Add custom seasonality if needed
            self.model.add_seasonality(name='monthly', period=30.5, fourier_order=3)

            self.model.fit(df)
            logger.info("Expense forecasting model trained")
            return True

        except Exception as e:
            logger.error(f"Error training forecasting model: {e}")
            return False

    def forecast(self, periods: int = 30) -> Dict:
        """
        Generate expense forecast.

        Args:
            periods: Number of periods to forecast

        Returns:
            Forecast dictionary with predictions
        """
        if not self.model:
            return {'error': 'Model not trained'}

        try:
            # Create future dataframe
            future = self.model.make_future_dataframe(periods=periods)

            # Make predictions
            forecast = self.model.predict(future)

            # Get last known data
            last_known = forecast.iloc[-(periods + 1)]

            # Calculate statistics
            forecast_values = forecast.iloc[-periods:]['yhat'].values
            lower_bound = forecast.iloc[-periods:]['yhat_lower'].values
            upper_bound = forecast.iloc[-periods:]['yhat_upper'].values

            return {
                'periods': periods,
                'forecast': [
                    {
                        'date': row['ds'].isoformat(),
                        'predicted': float(row['yhat']),
                        'lower_bound': float(row['yhat_lower']),
                        'upper_bound': float(row['yhat_upper'])
                    }
                    for _, row in forecast.iloc[-periods:].iterrows()
                ],
                'average_forecast': float(forecast_values.mean()),
                'total_forecast': float(forecast_values.sum()),
                'confidence_interval': {
                    'lower': float(lower_bound.mean()),
                    'upper': float(upper_bound.mean())
                }
            }

        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
            return {'error': str(e)}

    def save_model(self, path: str):
        """Save model to file."""
        try:
            import pickle
            with open(path, 'wb') as f:
                pickle.dump(self.model, f)
            logger.info(f"Forecasting model saved to {path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")

    def load_model(self, path: str):
        """Load model from file."""
        try:
            import pickle
            with open(path, 'rb') as f:
                self.model = pickle.load(f)
            logger.info(f"Forecasting model loaded from {path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")


class SavingsTrajectory:
    """Calculate and forecast savings trajectory."""

    def __init__(self, user_id: int):
        """Initialize savings trajectory calculator."""
        self.user_id = user_id

    def calculate_monthly_savings(
        self,
        start_date: datetime,
        end_date: datetime,
        session=None
    ) -> Dict:
        """
        Calculate monthly savings over a period.

        Args:
            start_date: Start date
            end_date: End date
            session: Database session

        Returns:
            Dictionary with savings data
        """
        transactions = session.query(Transaction).filter(
            Transaction.user_id == self.user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).all()

        income = sum(t.amount for t in transactions if t.transaction_type == 'income')
        expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')

        return {
            'period': f"{start_date.date()} to {end_date.date()}",
            'total_income': income,
            'total_expenses': expenses,
            'total_savings': income - expenses,
            'savings_rate': round((income - expenses) / income * 100, 2) if income > 0 else 0
        }

    def forecast_savings(
        self,
        months: int = 12,
        monthly_savings: float = None,
        session=None
    ) -> List[Dict]:
        """
        Forecast savings trajectory.

        Args:
            months: Number of months to forecast
            monthly_savings: Average monthly savings (if None, calculate from data)
            session: Database session

        Returns:
            List of monthly savings forecasts
        """
        # Calculate average monthly savings if not provided
        if monthly_savings is None:
            current_date = datetime.now()
            start_date = current_date.replace(day=1) - timedelta(days=30 * 6)

            savings_data = self.calculate_monthly_savings(start_date, current_date, session)
            monthly_savings = savings_data['total_savings'] / 6

        forecast = []
        current_date = datetime.now()

        for i in range(1, months + 1):
            forecast_date = current_date.replace(day=1) + timedelta(days=30 * i)
            projected_savings = monthly_savings * (1 + 0.02 * i)  # 2% growth per month

            forecast.append({
                'month': i,
                'date': forecast_date.isoformat(),
                'projected_savings': round(projected_savings, 2),
                'cumulative_savings': round(projected_savings * i, 2)
            })

        return forecast

    def calculate_goal_progress(
        self,
        goal_id: int,
        session=None
    ) -> Dict:
        """
        Calculate progress towards a financial goal.

        Args:
            goal_id: Goal ID
            session: Database session

        Returns:
            Goal progress data
        """
        goal = session.query(Goal).filter(Goal.id == goal_id).first()

        if not goal:
            return {'error': 'Goal not found'}

        # Calculate total contributions
        transactions = session.query(Transaction).filter(
            Transaction.user_id == self.user_id,
            Transaction.category_id == goal_id,
            Transaction.transaction_type == 'income'
        ).all()

        total_contributions = sum(t.amount for t in transactions)

        progress = (total_contributions / goal.target_amount) * 100

        return {
            'goal_id': goal.id,
            'name': goal.name,
            'target_amount': goal.target_amount,
            'current_amount': total_contributions,
            'progress': round(progress, 2),
            'remaining': round(goal.target_amount - total_contributions, 2),
            'time_remaining': (goal.target_date - datetime.now()).days,
            'monthly_needed': round((goal.target_amount - total_contributions) / max(1, (goal.target_date - datetime.now()).days / 30), 2)
        }


class RetirementSimulator:
    """Retirement corpus simulator using compound interest formulas."""

    def __init__(self):
        """Initialize retirement simulator."""
        pass

    def simulate(
        self,
        current_age: int,
        retirement_age: int,
        monthly_contribution: float,
        current_savings: float = 0.0,
        expected_return: float = 0.08,
        inflation_rate: float = 0.06,
        years_in_retirement: int = 20
    ) -> Dict:
        """
        Simulate retirement corpus.

        Args:
            current_age: Current age
            retirement_age: Retirement age
            monthly_contribution: Monthly contribution amount
            current_savings: Current savings amount
            expected_return: Expected annual return (before inflation)
            inflation_rate: Annual inflation rate
            years_in_retirement: Number of years in retirement

        Returns:
            Retirement simulation results
        """
        years_to_retirement = retirement_age - current_age
        months_to_retirement = years_to_retirement * 12

        # Calculate future value of current savings
        future_savings = current_savings * ((1 + expected_return) ** years_to_retirement)

        # Calculate future value of monthly contributions
        monthly_return = expected_return / 12
        future_contributions = monthly_contribution * (
            ((1 + monthly_return) ** months_to_retirement - 1) / monthly_return
        )

        total_retirement_corpus = future_savings + future_contributions

        # Adjust for inflation
        inflation_factor = (1 + inflation_rate) ** years_to_retirement
        real_retirement_corpus = total_retirement_corpus / inflation_factor

        # Calculate monthly withdrawal in retirement
        monthly_withdrawal = real_retirement_corpus / (years_in_retirement * 12)

        # Calculate if corpus will last
        corpus_will_last = True
        if monthly_withdrawal > real_retirement_corpus / (years_in_retirement * 12):
            corpus_will_last = False

        return {
            'current_age': current_age,
            'retirement_age': retirement_age,
            'years_to_retirement': years_to_retirement,
            'monthly_contribution': monthly_contribution,
            'current_savings': current_savings,
            'expected_return': expected_return,
            'inflation_rate': inflation_rate,
            'years_in_retirement': years_in_retirement,
            'total_retirement_corpus': round(total_retirement_corpus, 2),
            'real_retirement_corpus': round(real_retirement_corpus, 2),
            'monthly_withdrawal': round(monthly_withdrawal, 2),
            'corpus_will_last': corpus_will_last,
            'monthly_needed': round(monthly_contribution, 2),
            'monthly_savings_needed': round(monthly_contribution * 0.8, 2)  # Suggest 80% of current
        }

    def generate_scenario(
        self,
        current_age: int,
        retirement_age: int,
        monthly_contribution: float,
        current_savings: float = 0.0,
        scenarios: List[Dict] = None
    ) -> Dict:
        """
        Generate multiple retirement scenarios.

        Args:
            current_age: Current age
            retirement_age: Retirement age
            monthly_contribution: Monthly contribution
            current_savings: Current savings
            scenarios: List of scenario parameters

        Returns:
            Dictionary with multiple scenarios
        """
        if scenarios is None:
            scenarios = [
                {'name': 'Conservative', 'return': 0.06, 'inflation': 0.05},
                {'name': 'Moderate', 'return': 0.08, 'inflation': 0.06},
                {'name': 'Aggressive', 'return': 0.10, 'inflation': 0.07}
            ]

        results = []

        for scenario in scenarios:
            result = self.simulate(
                current_age=current_age,
                retirement_age=retirement_age,
                monthly_contribution=monthly_contribution,
                current_savings=current_savings,
                expected_return=scenario['return'],
                inflation_rate=scenario['inflation']
            )
            result['scenario'] = scenario['name']
            results.append(result)

        return {
            'current_age': current_age,
            'retirement_age': retirement_age,
            'monthly_contribution': monthly_contribution,
            'current_savings': current_savings,
            'scenarios': results
        }


def forecast_expenses(
    user_id: int,
    horizon_days: int = 30,
    session=None
) -> Dict:
    """
    Get expense forecast for a user.

    Args:
        user_id: User ID
        horizon_days: Number of days to forecast
        session: Database session

    Returns:
        Forecast dictionary
    """
    # Get expense transactions
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # Use last 90 days for training

    transactions = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == 'expense',
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()

    # Train forecaster
    forecaster = ExpenseForecaster()
    forecaster.train(transactions)

    # Generate forecast
    forecast = forecaster.forecast(periods=horizon_days // 30)

    return forecast


def forecast_savings(
    user_id: int,
    horizon_days: int = 30,
    session=None
) -> Dict:
    """
    Get savings forecast for a user.

    Args:
        user_id: User ID
        horizon_days: Number of days to forecast
        session: Database session

    Returns:
        Savings forecast dictionary
    """
    # Get transactions
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    transactions = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()

    # Calculate average monthly savings
    income = sum(t.amount for t in transactions if t.transaction_type == 'income')
    expenses = sum(t.amount for t in transactions if t.transaction_type == 'expense')
    monthly_savings = (income - expenses) / 3  # Average over 3 months

    # Generate forecast
    trajectory = SavingsTrajectory(user_id)
    forecast = trajectory.forecast_savings(months=horizon_days // 30, monthly_savings=monthly_savings, session=session)

    return {
        'monthly_savings': monthly_savings,
        'forecast': forecast
    }