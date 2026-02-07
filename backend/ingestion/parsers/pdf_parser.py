import pdfplumber
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

from ingestion.bank_detector import bank_detector, BankDetectionResult


class PDFParser:
    """Universal PDF statement parser supporting Indian banks, AMEX, and international formats."""

    # Maximum number of digits allowed in a transaction amount (to filter out reference numbers)
    MAX_TRANSACTION_DIGITS = 12  # No personal transaction exceeds 999,999,999,999
    
    # Maximum transaction amount to accept (prevents parsing errors and reference numbers)
    MAX_TRANSACTION_AMOUNT = 10_000_000  # 10 million

    # All date formats we try, ordered from most specific to least
    DATE_FORMATS = [
        '%d/%m/%Y',     # 07/01/2025 (Indian)
        '%m/%d/%Y',     # 01/07/2025 (US)
        '%d-%m-%Y',     # 07-01-2025
        '%m-%d-%Y',     # 01-07-2025
        '%Y-%m-%d',     # 2025-01-07 (ISO)
        '%d/%m/%y',     # 07/01/25
        '%m/%d/%y',     # 01/07/25
        '%d-%m-%y',     # 07-01-25
        '%d %b %Y',     # 07 Jan 2025
        '%d %B %Y',     # 07 January 2025
        '%d %b %y',     # 07 Jan 25
        '%b %d, %Y',    # Jan 07, 2025 (US formal)
        '%B %d, %Y',    # January 07, 2025
        '%d %b',        # 07 Jan (no year)
        '%d/%m',        # 07/01 (no year)
        '%m/%d',        # 01/07 (no year)
    ]

    # Header variations for column detection (lowercase)
    HEADER_KEYWORDS = {
        'date': ['date', 'txn date', 'transaction date', 'posting date', 'value date',
                 'trans date', 'valuedate', 'post date', 'stmt date', 'book date',
                 'booking date', 'effective date', 'trn date'],
        'description': ['description', 'narrative', 'details', 'memo', 'particulars',
                        'transaction details', 'transaction description', 'merchant',
                        'payee', 'desc', 'remarks', 'narration', 'transaction',
                        'transaction narrative'],
        'amount': ['amount', 'txn amount', 'transaction amount', 'sum', 'value',
                   'total'],
        'credit': ['credit', 'deposit', 'cr', 'credits', 'payments', 'payment',
                   'credit amount', 'cr amount', 'money in'],
        'debit': ['debit', 'withdrawal', 'dr', 'debits', 'charges', 'charge', 'purchases',
                  'debit amount', 'dr amount', 'money out'],
        'reference': ['ref', 'reference', 'ref no', 'chq no', 'cheque no', 'txn id',
                      'card no', 'card number', 'check no', 'instrument'],
    }

    def __init__(self):
        pass

    def _try_parse_date(self, date_str: str) -> Optional[datetime]:
        """Try multiple date formats and return the first match."""
        if not date_str or not date_str.strip():
            return None

        date_str = date_str.strip()
        # Clean extra whitespace
        date_str = re.sub(r'\s+', ' ', date_str)

        for fmt in self.DATE_FORMATS:
            try:
                dt = datetime.strptime(date_str, fmt)
                # If year is missing (format like '%d %b'), assume current year
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt
            except ValueError:
                continue

        # Last resort: pandas date parser
        try:
            dt = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
            if pd.notna(dt):
                return dt.to_pydatetime()
        except Exception:
            pass

        return None

    def _parse_amount(self, val: str) -> Optional[float]:
        """Parse amount string to float, handling various formats."""
        if not val or not val.strip():
            return None

        val = val.strip()

        # Detect Cr / Dr
        is_negative = False
        is_credit = False
        val_lower = val.lower()
        if 'dr' in val_lower:
            is_negative = True
        if 'cr' in val_lower:
            is_credit = True

        # Detect parenthetical negatives: (123.45)
        if '(' in val and ')' in val:
            is_negative = True

        # Strip to digits, dots, commas, minus
        cleaned = re.sub(r'[^\d.,\-]', '', val)
        if not cleaned:
            return None

        # Remove commas (Indian: 1,23,456.78 or International: 1,234,567.89)
        cleaned = cleaned.replace(',', '')

        # Sanity: reject if the numeric part has too many digits (reference numbers leaking in)
        digits_only = re.sub(r'[^0-9]', '', cleaned)
        if len(digits_only) > self.MAX_TRANSACTION_DIGITS:
            return None

        try:
            amount = float(cleaned)
        except ValueError:
            return None

        # Sanity check: reject absurd amounts
        if abs(amount) > self.MAX_TRANSACTION_AMOUNT:
            return None

        if is_negative:
            amount = -abs(amount)
        if is_credit:
            amount = abs(amount)

        return amount

    def _match_column(self, col_name: str, category: str) -> bool:
        """Check if a column name matches a category of header keywords."""
        col_lower = col_name.lower().strip()
        for keyword in self.HEADER_KEYWORDS.get(category, []):
            if keyword in col_lower:
                return True
        return False

    def _detect_currency(self, text: str) -> str:
        """Detect currency from statement text."""
        text_upper = text.upper()
        # Gulf currencies (check first — common for this app's users)
        if 'QAR' in text_upper or 'QATARI' in text_upper or 'QATAR' in text_upper:
            return 'QAR'
        if 'AED' in text_upper or 'DIRHAM' in text_upper or 'UAE' in text_upper:
            return 'AED'
        if 'SAR' in text_upper or 'SAUDI RIYAL' in text_upper:
            return 'SAR'
        if 'KWD' in text_upper or 'KUWAITI' in text_upper:
            return 'KWD'
        if 'BHD' in text_upper or 'BAHRAINI' in text_upper:
            return 'BHD'
        if 'OMR' in text_upper or 'OMANI' in text_upper:
            return 'OMR'
        # Major global currencies
        if 'USD' in text_upper or '$ ' in text_upper or 'U.S. DOLLAR' in text_upper:
            return 'USD'
        if 'EUR' in text_upper or '€' in text_upper:
            return 'EUR'
        if 'GBP' in text_upper or '£' in text_upper:
            return 'GBP'
        if 'INR' in text_upper or '₹' in text_upper or 'RUPEE' in text_upper:
            return 'INR'
        if 'SGD' in text_upper or 'SINGAPORE' in text_upper:
            return 'SGD'
        if 'MYR' in text_upper or 'RINGGIT' in text_upper:
            return 'MYR'
        return 'INR'  # Default

    def _auto_detect_columns(self, table: list) -> dict:
        """
        Smart column detection: scan data rows to guess which column holds
        dates, amounts, descriptions when headers are unrecognizable.
        """
        if not table or len(table) < 3:
            return {}

        num_cols = max(len(r) for r in table if r)
        date_scores = [0] * num_cols
        amount_scores = [0] * num_cols
        text_scores = [0] * num_cols

        sample_rows = table[1:min(8, len(table))]
        date_re = re.compile(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}')
        amount_re = re.compile(r'^-?[\d,]+\.\d{2}$')

        for row in sample_rows:
            if not row:
                continue
            for i, cell in enumerate(row):
                if i >= num_cols:
                    break
                val = str(cell).strip() if cell else ""
                if not val:
                    continue
                if date_re.search(val):
                    date_scores[i] += 1
                cleaned = re.sub(r'[,\s]', '', val)
                if amount_re.match(cleaned) or amount_re.match(val):
                    amount_scores[i] += 1
                if len(val) > 10 and not amount_re.match(cleaned):
                    text_scores[i] += 1

        result = {}
        threshold = len(sample_rows) * 0.3

        # Best date column
        best_date = max(range(num_cols), key=lambda i: date_scores[i])
        if date_scores[best_date] >= threshold:
            result['date_idx'] = best_date

        # Best description column (longest text, not date/amount)
        best_desc = max(range(num_cols), key=lambda i: text_scores[i])
        if text_scores[best_desc] >= threshold:
            result['desc_idx'] = best_desc

        # Amount columns — pick up to 2 highest scoring that aren't date/desc
        amt_candidates = sorted(
            [i for i in range(num_cols) if i != result.get('date_idx') and i != result.get('desc_idx')],
            key=lambda i: amount_scores[i], reverse=True
        )
        if amt_candidates and amount_scores[amt_candidates[0]] >= threshold:
            result['amt1_idx'] = amt_candidates[0]
            if len(amt_candidates) > 1 and amount_scores[amt_candidates[1]] >= threshold:
                result['amt2_idx'] = amt_candidates[1]

        return result

    def _parse_table(self, table: list, currency: str) -> List[Dict[str, Any]]:
        """Parse a single extracted table into transactions."""
        transactions: List[Dict[str, Any]] = []

        if not table or len(table) < 2:
            return transactions

        # Build column mapping from header row
        headers = [str(h).strip() if h else '' for h in table[0]]

        date_idx = -1
        desc_idx = -1
        amt_idx = -1
        credit_idx = -1
        debit_idx = -1
        ref_idx = -1

        for i, header in enumerate(headers):
            h_lower = header.lower()
            if date_idx == -1 and self._match_column(header, 'date'):
                date_idx = i
            if desc_idx == -1 and self._match_column(header, 'description'):
                desc_idx = i
            # Credit/Debit columns take priority over generic "amount"
            if self._match_column(header, 'credit') and 'balance' not in h_lower:
                credit_idx = i
            elif self._match_column(header, 'debit') and 'balance' not in h_lower:
                debit_idx = i
            elif amt_idx == -1 and self._match_column(header, 'amount') and 'balance' not in h_lower:
                amt_idx = i
            if ref_idx == -1 and self._match_column(header, 'reference'):
                ref_idx = i

        # ─── Smart fallback: auto-detect columns from data if headers fail ───
        if date_idx == -1:
            auto = self._auto_detect_columns(table)
            if 'date_idx' in auto:
                date_idx = auto['date_idx']
                print(f"[PDFParser] Auto-detected date column: {date_idx}")
            if desc_idx == -1 and 'desc_idx' in auto:
                desc_idx = auto['desc_idx']
                print(f"[PDFParser] Auto-detected description column: {desc_idx}")
            if amt_idx == -1 and credit_idx == -1 and debit_idx == -1:
                if 'amt1_idx' in auto and 'amt2_idx' in auto:
                    # Two amount columns → debit/credit
                    debit_idx = auto['amt1_idx']
                    credit_idx = auto['amt2_idx']
                    print(f"[PDFParser] Auto-detected debit={debit_idx}, credit={credit_idx}")
                elif 'amt1_idx' in auto:
                    amt_idx = auto['amt1_idx']
                    print(f"[PDFParser] Auto-detected amount column: {amt_idx}")

        if date_idx == -1:
            return transactions  # Can't parse without dates

        for row in table[1:]:
            try:
                if not row or all(not cell for cell in row):
                    continue

                # ---- Date ----
                date_str = str(row[date_idx]) if date_idx < len(row) and row[date_idx] else ""
                dt = self._try_parse_date(date_str)
                if not dt:
                    continue

                # ---- Description ----
                desc = ""
                if desc_idx != -1 and desc_idx < len(row) and row[desc_idx]:
                    desc = str(row[desc_idx]).replace('\n', ' ').strip()

                # ---- Amount ----
                amount = 0.0
                if amt_idx != -1 and amt_idx < len(row) and row[amt_idx]:
                    parsed = self._parse_amount(str(row[amt_idx]))
                    if parsed is not None:
                        amount = parsed
                elif credit_idx != -1 or debit_idx != -1:
                    credit_val = 0.0
                    debit_val = 0.0
                    if credit_idx != -1 and credit_idx < len(row) and row[credit_idx]:
                        parsed = self._parse_amount(str(row[credit_idx]))
                        if parsed is not None:
                            credit_val = abs(parsed)
                    if debit_idx != -1 and debit_idx < len(row) and row[debit_idx]:
                        parsed = self._parse_amount(str(row[debit_idx]))
                        if parsed is not None:
                            debit_val = abs(parsed)
                    amount = credit_val - debit_val

                if amount == 0.0 and not desc:
                    continue  # skip empty rows

                # ---- Transaction Type ----
                txn_type = "expense" if amount < 0 else "income" if amount > 0 else "expense"

                # ---- Reference ----
                ref = ""
                if ref_idx != -1 and ref_idx < len(row) and row[ref_idx]:
                    ref = str(row[ref_idx]).strip()

                transactions.append({
                    "date": dt,
                    "description": desc or "Unknown Transaction",
                    "amount": amount,
                    "type": txn_type,
                    "currency": currency,
                    "reference": ref,
                    "raw_data": {"row": [str(c) for c in row]}
                })
            except Exception:
                continue

        return transactions

    def _parse_text_fallback(self, page_text: str, currency: str) -> List[Dict[str, Any]]:
        """Fallback: parse transactions from raw text lines when tables fail.
        Handles multi-line descriptions common in Gulf bank statements."""
        transactions: List[Dict[str, Any]] = []
        if not page_text:
            return transactions

        lines = page_text.split('\n')

        # Date regex: multiple patterns combined
        date_pattern = re.compile(
            r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})'          # dd/mm/yyyy or mm/dd/yyyy
            r'|(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})'        # dd Mon yyyy
            r'|([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4})'      # Mon dd, yyyy
        )

        # Amount pattern: handle spaces in numbers (1 234.56), commas, optional CR/DR
        amount_pattern = re.compile(r'(-?[\d,\s]+\.\d{2})')

        current_txn = None

        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue

            # Skip common header/footer lines
            line_lower = line.lower()
            if any(kw in line_lower for kw in ['opening balance', 'closing balance',
                    'statement of account', 'account statement', 'page ', 'continued',
                    'account number', 'account no', 'branch', 'iban', 'swift']):
                continue

            date_match = date_pattern.search(line)

            if date_match:
                # Save previous transaction if we had one accumulating
                if current_txn and current_txn.get('amount'):
                    current_txn['type'] = 'expense' if current_txn['amount'] < 0 else 'income'
                    transactions.append(current_txn)
                    current_txn = None

                matched_date_str = date_match.group(0)
                dt = self._try_parse_date(matched_date_str)
                if not dt:
                    continue

                remaining = line[date_match.end():].strip()
                # Check if there's a second date (value date) right after
                date_match2 = date_pattern.match(remaining)
                if date_match2:
                    remaining = remaining[date_match2.end():].strip()

                amounts = amount_pattern.findall(remaining)
                if not amounts:
                    amounts = amount_pattern.findall(line)

                parsed_amount = None
                if amounts:
                    # Take the first amount, clean spaces inside it
                    raw_amount = amounts[-1].replace(' ', '')  # Use last amount (often balance is first)
                    parsed_amount = self._parse_amount(raw_amount)

                    if parsed_amount is not None:
                        # Check for Cr/Dr to assign sign
                        if 'Dr' in line or 'DR' in line or 'debit' in line_lower:
                            parsed_amount = -abs(parsed_amount)
                        elif 'Cr' in line or 'CR' in line or 'credit' in line_lower:
                            parsed_amount = abs(parsed_amount)

                # Description: strip date and amounts from the line
                description = remaining
                for amt_str in (amounts or []):
                    description = description.replace(amt_str, '')
                description = re.sub(r'\s+', ' ', description).strip()
                description = description.strip('| \t-')

                if parsed_amount is not None and parsed_amount != 0:
                    transactions.append({
                        "date": dt,
                        "description": description if len(description) > 1 else "Transaction",
                        "amount": parsed_amount,
                        "type": "expense" if parsed_amount < 0 else "income",
                        "currency": currency,
                        "reference": "",
                        "raw_data": {"line": line}
                    })
                elif description and len(description) > 2:
                    # Start accumulating — amount might be on the next line
                    current_txn = {
                        "date": dt,
                        "description": description,
                        "amount": None,
                        "currency": currency,
                        "reference": "",
                        "raw_data": {"line": line}
                    }
            elif current_txn:
                # Continuation line: might contain description or amount
                amounts = amount_pattern.findall(line)
                if amounts:
                    raw_amount = amounts[-1].replace(' ', '')
                    parsed_amount = self._parse_amount(raw_amount)
                    if parsed_amount is not None and parsed_amount != 0:
                        if 'Dr' in line or 'DR' in line:
                            parsed_amount = -abs(parsed_amount)
                        elif 'Cr' in line or 'CR' in line:
                            parsed_amount = abs(parsed_amount)
                        current_txn['amount'] = parsed_amount
                        # Append any non-amount text as description
                        desc_extra = line
                        for a in amounts:
                            desc_extra = desc_extra.replace(a, '')
                        desc_extra = desc_extra.strip('| \t-').strip()
                        if desc_extra and len(desc_extra) > 2:
                            current_txn['description'] += ' ' + desc_extra
                else:
                    # Pure description continuation line
                    current_txn['description'] += ' ' + line.strip()

        # Don't forget the last accumulated transaction
        if current_txn and current_txn.get('amount'):
            current_txn['type'] = 'expense' if current_txn['amount'] < 0 else 'income'
            transactions.append(current_txn)

        return transactions

    def parse(self, file_path: str, password: str = None, filename: str = None) -> Tuple[List[Dict[str, Any]], BankDetectionResult]:
        """Parse a PDF statement. Handles password-protected files. Returns transactions + bank detection."""
        all_transactions: List[Dict[str, Any]] = []
        all_page_text = ""  # Accumulate text for bank detection

        try:
            open_kwargs = {}
            if password:
                open_kwargs['password'] = password

            with pdfplumber.open(file_path, **open_kwargs) as pdf:
                # Detect currency from first page
                first_page_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
                currency = self._detect_currency(first_page_text)

                print(f"[PDFParser] Opened PDF: {len(pdf.pages)} pages, detected currency: {currency}")

                # Accumulate text from first 3 pages for bank detection (covers most headers)
                for i, page in enumerate(pdf.pages[:3]):
                    page_text = page.extract_text() or ""
                    all_page_text += " " + page_text

                for page_num, page in enumerate(pdf.pages):
                    page_txns: List[Dict[str, Any]] = []

                    # Strategy 1: Default table extraction
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            if table and len(table) >= 2:
                                table_txns = self._parse_table(table, currency)
                                page_txns.extend(table_txns)

                    # Strategy 2: Try table extraction with different settings
                    if not page_txns:
                        try:
                            tables = page.extract_tables(table_settings={
                                "vertical_strategy": "text",
                                "horizontal_strategy": "text",
                                "snap_tolerance": 5,
                            })
                            if tables:
                                for table in tables:
                                    if table and len(table) >= 2:
                                        table_txns = self._parse_table(table, currency)
                                        page_txns.extend(table_txns)
                        except Exception:
                            pass

                    # Strategy 3: Try with lines-based extraction (common for bordered tables)
                    if not page_txns:
                        try:
                            tables = page.extract_tables(table_settings={
                                "vertical_strategy": "lines",
                                "horizontal_strategy": "lines",
                            })
                            if tables:
                                for table in tables:
                                    if table and len(table) >= 2:
                                        table_txns = self._parse_table(table, currency)
                                        page_txns.extend(table_txns)
                        except Exception:
                            pass

                    # Strategy 4: text fallback if all table strategies yielded nothing
                    if not page_txns:
                        page_text = page.extract_text() or ""
                        text_txns = self._parse_text_fallback(page_text, currency)
                        page_txns.extend(text_txns)

                    print(f"[PDFParser] Page {page_num + 1}: {len(page_txns)} transactions found")
                    all_transactions.extend(page_txns)

                print(f"[PDFParser] Total transactions extracted: {len(all_transactions)}")

        except Exception as e:
            # Detect password-protected PDFs - PdfminerException wraps PDFPasswordIncorrect
            # but often str(e) is empty, so check the exception chain
            is_password_error = False
            msg = str(e).lower()
            if "password" in msg or "encrypted" in msg or "decrypt" in msg:
                is_password_error = True
            # Check exception type name
            exc_type_name = type(e).__name__.lower()
            if "pdfminer" in exc_type_name or "encrypt" in exc_type_name:
                is_password_error = True
            # Check cause chain for PDFPasswordIncorrect
            cause = e.__cause__
            while cause:
                cause_name = type(cause).__name__.lower()
                cause_msg = str(cause).lower()
                if "password" in cause_name or "password" in cause_msg or "encrypt" in cause_name:
                    is_password_error = True
                    break
                cause = getattr(cause, '__cause__', None)

            if is_password_error:
                if password:
                    raise ValueError("PDF is encrypted and the provided password is incorrect.") from e
                else:
                    raise ValueError("PDF is password-protected. Please provide the password.") from e

            print(f"[PDFParser] Error: {e}")
            import traceback; traceback.print_exc()
            raise ValueError(f"Failed to parse PDF: {e}") from e

        # ─── Bank & Account Detection ───
        detection = bank_detector.detect(
            filename=filename or file_path,
            full_text=all_page_text,
            transactions=all_transactions,
        )

        return all_transactions, detection
