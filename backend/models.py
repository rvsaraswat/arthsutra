"""
Database models for the Personal Finance Manager.
Uses SQLAlchemy with SQLCipher for encrypted storage.
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
# import sqlcipher3  # Commented out - using regular SQLite for now

from config import settings

Base = declarative_base()


class User(Base):
    """User account information."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    preferences = Column(Text)  # JSON string for user preferences

    # Relationships
    transactions = relationship("Transaction", back_populates="user")
    budgets = relationship("Budget", back_populates="user")
    goals = relationship("Goal", back_populates="user")
    categories = relationship("Category", back_populates="user")


class Category(Base):
    """Transaction categories for classification."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    type = Column(String(20), nullable=False)  # "income" or "expense"
    icon = Column(String(50))
    color = Column(String(7))  # Hex color code
    is_custom = Column(Boolean, default=False)
    confidence_threshold = Column(Float, default=0.7)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")

    __table_args__ = (
        Index("idx_user_category_type", "user_id", "type"),
    )


class Transaction(Base):
    """Individual financial transactions."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    description = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="INR")
    transaction_type = Column(String(20), nullable=False)  # "income" or "expense"
    date = Column(DateTime, nullable=False)
    account = Column(String(50))  # Bank account name
    reference = Column(String(100))  # Transaction reference/ID
    tags = Column(Text)  # JSON string for tags
    notes = Column(Text)
    is_recurring = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    confidence_score = Column(Float)  # ML model confidence
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

    __table_args__ = (
        Index("idx_user_date", "user_id", "date"),
        Index("idx_user_type", "user_id", "transaction_type"),
        Index("idx_category_date", "category_id", "date"),
    )


class Budget(Base):
    """Budget limits and tracking."""

    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    name = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    period = Column(String(20), nullable=False)  # "monthly", "yearly"
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category")

    __table_args__ = (
        Index("idx_user_budget_period", "user_id", "period"),
    )


class Goal(Base):
    """Financial goals (retirement, education, etc.)."""

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    target_date = Column(DateTime, nullable=False)
    category = Column(String(50))  # "retirement", "education", "home", etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="goals")

    __table_args__ = (
        Index("idx_user_goal_category", "user_id", "category"),
    )


class Asset(Base):
    """Financial assets (property, gold, crypto, etc.)."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # "property", "gold", "crypto", "stock", etc.
    quantity = Column(Float, nullable=False)
    unit = Column(String(20))  # "sqft", "grams", "coins", "shares", etc.
    purchase_price = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    currency = Column(String(3), default="INR")
    purchase_date = Column(DateTime, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index("idx_user_asset_type", "user_id", "type"),
    )


class AuditLog(Base):
    """Audit trail for security and compliance."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)  # "login", "transaction_add", etc.
    resource_type = Column(String(50))  # "transaction", "user", etc.
    resource_id = Column(Integer)
    details = Column(Text)  # JSON string
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
        Index("idx_action_timestamp", "action", "timestamp"),
    )


class FinancialSnapshot(Base):
    """Historical financial snapshots for analysis."""

    __tablename__ = "financial_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    net_worth = Column(Float, nullable=False)
    total_income = Column(Float, nullable=False)
    total_expenses = Column(Float, nullable=False)
    cash_flow = Column(Float, nullable=False)
    savings_rate = Column(Float)
    budget_utilization = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index("idx_user_date", "user_id", "date"),
    )


# Database connection functions
def get_encrypted_connection(db_path: str, key: str):
    """Create an encrypted SQLite connection using SQLCipher."""
    # TODO: Implement SQLCipher when available
    # For now, using regular SQLite
    import sqlite3
    return sqlite3.connect(db_path)


def create_engine_with_encryption():
    """Create SQLAlchemy engine with SQLite support."""
    # Using regular SQLite for now
    return create_engine(
        f"sqlite:///{settings.DATABASE_PATH}",
        connect_args={
            "check_same_thread": False,
        },
    )


# Create tables
def create_tables():
    """Create all database tables."""
    engine = create_engine_with_encryption()
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get a database session."""
    engine = create_engine_with_encryption()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()