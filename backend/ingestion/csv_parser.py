"""
CSV transaction parser for bank statements and expense records.
Supports multiple CSV formats and auto-detection.
"""
import csv
import re
from datetime import datetime
from typing import List, Dict, Optional
from decimal import Decimal
import logging

from models import Transaction, Category, get_session

logger = logging.getLogger(__name__)


class CSVParser:
    """Parser for CSV transaction files."""

    def __init__(self, file_path: str):
        """Initialize CSV parser with file path."""
        self.file_path = file_path
        self.encoding = 'utf-8'

    def parse(self) -> List[Dict]:
        """Parse CSV file and return list of transactions."""
        try:
            with open(self.file_path, mode='r', encoding=self.encoding, newline='') as file:
                reader = csv.DictReader(file)

                # Detect column names and normalize
                transactions = []
                for row in reader:
                    transaction = self._normalize_row(row)
                    if transaction:
                        transactions.append(transaction)

                logger.info(f"Parsed {len(transactions)} transactions from {self.file_path}")
                return transactions

        except Exception as e:
            logger.error(f"Error parsing CSV file {self.file_path}: {e}")
            raise

    def _normalize_row(self, row: Dict) -> Optional[Dict]:
        """Normalize a CSV row into a transaction dictionary."""
        # Common column name variations
        date_patterns = ['date', 'transaction_date', 'post_date', 'entry_date', 'booking_date']
        amount_patterns = ['amount', 'debit', 'credit', 'value', 'transaction_amount']
        description_patterns = ['description', 'narration', 'particulars', 'transaction_description', 'memo']

        # Find actual column names
        date_col = self._find_column(row, date_patterns)
        amount_col = self._find_column(row, amount_patterns)
        desc_col = self._find_column(row, description_patterns)

        if not date_col or not amount_col:
            logger.warning(f"Skipping row - missing date or amount: {row}")
            return None

        # Parse date
        try:
            date = self._parse_date(row[date_col])
        except ValueError:
            logger.warning(f"Skipping row - invalid date: {row[date_col]}")
            return None

        # Parse amount
        try:
            amount = self._parse_amount(row[amount_col])
        except ValueError:
            logger.warning(f"Skipping row - invalid amount: {row[amount_col]}")
            return None

        # Determine transaction type
        transaction_type = self._determine_type(amount)

        # Build transaction dict
        transaction = {
            'date': date,
            'amount': abs(amount),
            'currency': 'INR',  # Default to INR, can be enhanced
            'type': transaction_type,
            'description': row.get(desc_col, 'Unknown transaction'),
            'account': row.get('account', 'Unknown account'),
            'reference': row.get('reference', row.get('transaction_id', '')),
            'tags': row.get('tags', ''),
            'notes': row.get('notes', ''),
            'is_recurring': False,
            'is_duplicate': False,
            'confidence_score': 1.0
        }

        return transaction

    def _find_column(self, row: Dict, patterns: List[str]) -> Optional[str]:
        """Find column name matching any of the patterns."""
        for key in row.keys():
            key_lower = key.lower()
            for pattern in patterns:
                if pattern.lower() in key_lower:
                    return key
        return None

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string into datetime object."""
        date_str = str(date_str).strip()

        # Try multiple date formats
        formats = [
            '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y',
            '%d-%b-%Y', '%b-%d-%Y', '%d %b %Y', '%b %d, %Y',
            '%d-%b-%y', '%b-%d-%y', '%d %b %y', '%b %d, %y',
            '%Y%m%d', '%d%m%Y', '%m%d%Y'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Unable to parse date: {date_str}")

    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string into float."""
        amount_str = str(amount_str).strip()

        # Remove currency symbols and commas
        amount_str = re.sub(r'[^\d.-]', '', amount_str)

        try:
            return float(amount_str)
        except ValueError:
            raise ValueError(f"Unable to parse amount: {amount_str}")

    def _determine_type(self, amount: float) -> str:
        """Determine if transaction is income or expense."""
        return 'income' if amount > 0 else 'expense'


class BankStatementParser(CSVParser):
    """Specialized parser for bank statements."""

    def __init__(self, file_path: str, bank_name: str):
        """Initialize with bank name for format-specific parsing."""
        super().__init__(file_path)
        self.bank_name = bank_name.lower()

    def parse(self) -> List[Dict]:
        """Parse bank statement with bank-specific logic."""
        transactions = super().parse()

        # Apply bank-specific transformations
        if 'hdfc' in self.bank_name:
            transactions = self._transform_hdfc(transactions)
        elif 'icici' in self.bank_name:
            transactions = self._transform_icici(transactions)
        elif 'sbi' in self.bank_name:
            transactions = self._transform_sbi(transactions)
        elif 'axis' in self.bank_name:
            transactions = self._transform_axis(transactions)

        return transactions

    def _transform_hdfc(self, transactions: List[Dict]) -> List[Dict]:
        """Transform HDFC bank statement format."""
        # HDFC specific transformations
        for t in transactions:
            # Sometimes description contains account number
            if 'HDFC0001' in t['description']:
                t['account'] = 'HDFC Savings'
        return transactions

    def _transform_icici(self, transactions: List[Dict]) -> List[Dict]:
        """Transform ICICI bank statement format."""
        # ICICI specific transformations
        for t in transactions:
            if 'ICICI0001' in t['description']:
                t['account'] = 'ICICI Savings'
        return transactions

    def _transform_sbi(self, transactions: List[Dict]) -> List[Dict]:
        """Transform SBI bank statement format."""
        # SBI specific transformations
        for t in transactions:
            if 'SBIN0001' in t['description']:
                t['account'] = 'SBI Savings'
        return transactions

    def _transform_axis(self, transactions: List[Dict]) -> List[Dict]:
        """Transform Axis bank statement format."""
        # Axis specific transformations
        for t in transactions:
            if 'AXIS0001' in t['description']:
                t['account'] = 'Axis Savings'
        return transactions


class ExpenseCSVParser(CSVParser):
    """Parser for expense tracking CSV files."""

    def __init__(self, file_path: str):
        """Initialize expense CSV parser."""
        super().__init__(file_path)

    def parse(self) -> List[Dict]:
        """Parse expense CSV with specific format."""
        transactions = super().parse()

        # Ensure all transactions are marked as expenses
        for t in transactions:
            t['type'] = 'expense'

        return transactions


def parse_csv_file(file_path: str, bank_name: str = None) -> List[Dict]:
    """
    Parse CSV file and return transactions.

    Args:
        file_path: Path to CSV file
        bank_name: Optional bank name for format-specific parsing

    Returns:
        List of transaction dictionaries
    """
    if bank_name:
        parser = BankStatementParser(file_path, bank_name)
    else:
        parser = CSVParser(file_path)

    return parser.parse()


def save_transactions_to_db(transactions: List[Dict], user_id: int, session):
    """
    Save transactions to database.

    Args:
        transactions: List of transaction dictionaries
        user_id: User ID
        session: Database session
    """
    saved_count = 0
    for tx_data in transactions:
        try:
            transaction = Transaction(
                user_id=user_id,
                description=tx_data['description'],
                amount=tx_data['amount'],
                currency=tx_data['currency'],
                transaction_type=tx_data['type'],
                date=tx_data['date'],
                account=tx_data['account'],
                reference=tx_data['reference'],
                tags=tx_data['tags'],
                notes=tx_data['notes'],
                is_recurring=tx_data['is_recurring'],
                is_duplicate=tx_data['is_duplicate'],
                confidence_score=tx_data['confidence_score']
            )
            session.add(transaction)
            saved_count += 1
        except Exception as e:
            logger.error(f"Error saving transaction: {e}")

    session.commit()
    logger.info(f"Saved {saved_count} transactions to database")
    return saved_count