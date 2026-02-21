"""
ML-based transaction categorization using TF-IDF and Logistic Regression.
Provides intelligent expense categorization with user feedback loop.
"""
import pickle
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

from ..models import Transaction, Category, get_session

logger = logging.getLogger(__name__)


class TransactionCategorizer:
    """ML-based transaction categorizer."""

    def __init__(self, model_path: str = None):
        """Initialize categorizer."""
        self.model_path = model_path
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.classifier = LogisticRegression(max_iter=1000, class_weight='balanced')
        self.is_trained = False

    def train(self, transactions: List[Transaction], categories: List[Category]):
        """
        Train the categorization model.

        Args:
            transactions: List of transactions with descriptions
            categories: List of categories with names
        """
        try:
            # Prepare training data
            X = []
            y = []

            for tx in transactions:
                if tx.description and tx.category:
                    X.append(tx.description.lower())
                    y.append(tx.category.name.lower())

            if len(X) < 10:
                logger.warning("Not enough training data for categorization")
                return False

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Vectorize text
            self.vectorizer.fit(X_train)
            X_train_vec = self.vectorizer.transform(X_train)
            X_test_vec = self.vectorizer.transform(X_test)

            # Train classifier
            self.classifier.fit(X_train_vec, y_train)

            # Evaluate
            y_pred = self.classifier.predict(X_test_vec)
            accuracy = accuracy_score(y_test, y_pred)

            logger.info(f"Categorization model trained with accuracy: {accuracy:.2%}")

            # Save model
            if self.model_path:
                self.save_model(self.model_path)

            self.is_trained = True
            return True

        except Exception as e:
            logger.error(f"Error training categorization model: {e}")
            return False

    def predict(self, description: str) -> Tuple[str, float]:
        """
        Predict category for a transaction description.

        Args:
            description: Transaction description

        Returns:
            Tuple of (category_name, confidence_score)
        """
        if not self.is_trained:
            return "Uncategorized", 0.0

        try:
            # Vectorize description
            description_lower = description.lower()
            vec = self.vectorizer.transform([description_lower])

            # Predict
            category_name = self.classifier.predict(vec)[0]
            confidence = self.classifier.predict_proba(vec)[0].max()

            return category_name, confidence

        except Exception as e:
            logger.error(f"Error predicting category: {e}")
            return "Uncategorized", 0.0

    def save_model(self, path: str):
        """Save trained model to file."""
        try:
            model_data = {
                'vectorizer': self.vectorizer,
                'classifier': self.classifier,
                'is_trained': self.is_trained
            }
            with open(path, 'wb') as f:
                pickle.dump(model_data, f)
            logger.info(f"Model saved to {path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")

    def load_model(self, path: str):
        """Load trained model from file."""
        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)

            self.vectorizer = model_data['vectorizer']
            self.classifier = model_data['classifier']
            self.is_trained = model_data['is_trained']

            logger.info(f"Model loaded from {path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")


class RuleBasedCategorizer:
    """Fallback rule-based categorization."""

    def __init__(self):
        """Initialize rule-based categorizer."""
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, List[str]]:
        """Load categorization rules."""
        return {
            'food': ['restaurant', 'dining', 'food', 'cafe', 'coffee', 'pizza', 'burger', 'biryani', 'thali', 'mess'],
            'transport': ['uber', 'ola', 'metro', 'bus', 'train', 'fuel', 'petrol', 'diesel', 'parking', 'taxi'],
            'shopping': ['amazon', 'flipkart', 'myntra', 'shop', 'store', 'retail', 'clothing', 'fashion', 'online'],
            'bills': ['electricity', 'water', 'internet', 'mobile', 'recharge', 'subscription', 'du', 'jio', 'airtel'],
            'entertainment': ['netflix', 'spotify', 'hotstar', 'movie', 'theatre', 'game', 'play', 'cinema'],
            'health': ['hospital', 'clinic', 'pharmacy', 'medicine', 'doctor', 'dental', 'insurance', 'medicare'],
            'salary': ['salary', 'payslip', 'bonus', 'incentive', 'commission'],
            'investment': ['stock', 'mutual fund', 'sip', 'recurring deposit', 'fd', 'investment', 'broker'],
            'education': ['course', 'book', 'university', 'college', 'school', 'tuition', 'training'],
            'travel': ['flight', 'airline', 'hotel', 'trip', 'vacation', 'tour', 'accommodation'],
            'groceries': ['grocery', 'supermarket', 'kirana', 'market', 'daily', 'vegetable', 'fruit'],
            'home': ['rent', 'maintenance', 'repair', 'furniture', 'decor', 'home'],
            'insurance': ['insurance', 'premium', 'claim', 'health insurance', 'life insurance'],
            'gift': ['gift', 'present', 'birthday', 'anniversary', 'wedding'],
            'other': []
        }

    def categorize(self, description: str) -> Tuple[str, float]:
        """
        Categorize using rules.

        Args:
            description: Transaction description

        Returns:
            Tuple of (category_name, confidence_score)
        """
        description_lower = description.lower()

        for category, keywords in self.rules.items():
            if category == 'other':
                continue

            for keyword in keywords:
                if keyword in description_lower:
                    return category, 0.8  # High confidence for rule-based

        return 'other', 0.5


class HybridCategorizer:
    """Hybrid categorizer combining ML and rules."""

    def __init__(self, ml_model_path: str = None):
        """Initialize hybrid categorizer."""
        self.ml_categorizer = TransactionCategorizer(ml_model_path)
        self.rule_categorizer = RuleBasedCategorizer()

    def train(self, transactions: List[Transaction], categories: List[Category]):
        """Train the ML model."""
        return self.ml_categorizer.train(transactions, categories)

    def categorize(self, description: str) -> Tuple[str, float]:
        """
        Categorize using hybrid approach.

        Args:
            description: Transaction description

        Returns:
            Tuple of (category_name, confidence_score)
        """
        # Try ML first
        if self.ml_categorizer.is_trained:
            category, confidence = self.ml_categorizer.predict(description)

            if confidence >= 0.7:
                return category, confidence

        # Fall back to rules
        category, confidence = self.rule_categorizer.categorize(description)

        return category, confidence


def categorize_transaction(
    description: str,
    user_id: int,
    session,
    use_ml: bool = True
) -> Tuple[str, float]:
    """
    Categorize a transaction.

    Args:
        description: Transaction description
        user_id: User ID
        session: Database session
        use_ml: Whether to use ML model

    Returns:
        Tuple of (category_name, confidence_score)
    """
    # Get user's categories
    categories = session.query(Category).filter(
        Category.user_id == user_id,
        Category.type == 'expense'
    ).all()

    category_names = [c.name for c in categories]

    if use_ml:
        # Try ML categorization
        ml_categorizer = TransactionCategorizer()
        ml_categorizer.load_model(settings.CATEGORIZATION_MODEL_PATH)

        category, confidence = ml_categorizer.categorize(description)

        # Check if predicted category exists
        if category in category_names:
            return category, confidence

    # Fall back to rule-based
    rule_categorizer = RuleBasedCategorizer()
    category, confidence = rule_categorizer.categorize(description)

    return category, confidence


def get_user_categories(user_id: int, session) -> List[Category]:
    """Get all categories for a user."""
    return session.query(Category).filter(Category.user_id == user_id).all()


def create_default_categories(user_id: int, session):
    """Create default expense categories for a new user."""
    default_categories = [
        {'name': 'Food & Dining', 'type': 'expense', 'icon': '🍔', 'color': '#FF6B6B'},
        {'name': 'Transportation', 'type': 'expense', 'icon': '🚗', 'color': '#4ECDC4'},
        {'name': 'Shopping', 'type': 'expense', 'icon': '🛍️', 'color': '#45B7D1'},
        {'name': 'Bills & Utilities', 'type': 'expense', 'icon': '💡', 'color': '#96CEB4'},
        {'name': 'Entertainment', 'type': 'expense', 'icon': '🎬', 'color': '#FFEEAD'},
        {'name': 'Healthcare', 'type': 'expense', 'icon': '🏥', 'color': '#D4A5A5'},
        {'name': 'Salary', 'type': 'income', 'icon': '💰', 'color': '#9B59B6'},
        {'name': 'Investments', 'type': 'income', 'icon': '📈', 'color': '#3498DB'},
        {'name': 'Other', 'type': 'expense', 'icon': '📦', 'color': '#95A5A6'},
    ]

    for cat_data in default_categories:
        category = Category(
            user_id=user_id,
            name=cat_data['name'],
            type=cat_data['type'],
            icon=cat_data['icon'],
            color=cat_data['color'],
            is_custom=False
        )
        session.add(category)

    session.commit()
    logger.info(f"Created default categories for user {user_id}")