import pandas as pd
import msoffcrypto
import io
from typing import List, Dict, Any, Tuple
from datetime import datetime
import numpy as np

from ..bank_detector import bank_detector, BankDetectionResult

# Common variations of column names
HEADER_MAPPINGS = {
    "date": ["date", "txn_date", "transaction_date", "posting_date", "valuedate", "value_date", "trans_date", "post_date"],
    "description": ["description", "narrative", "details", "memo", "particulars", "transaction_details", "narration", "remark", "remarks"],
    "amount": ["amount", "txn_amount", "transaction_amount", "sum", "value"],
    "credit": ["credit", "deposit", "cr", "credits"],
    "debit": ["debit", "withdrawal", "dr", "debits"],
    "balance": ["balance", "running_balance", "closing_balance"],
    "reference": ["ref", "reference", "ref_no", "chq_no", "cheque_no", "txn_id", "utr", "transaction_id"],
    "currency": ["currency", "ccy", "curr"],
}

class CSVParser:
    def __init__(self):
        pass

    def _decrypt_excel(self, file_path: str, password: str) -> pd.DataFrame:
        if not password:
             raise ValueError("Password required for encrypted file.")
        
        decrypted = io.BytesIO()
        with open(file_path, "rb") as f:
            file = msoffcrypto.OfficeFile(f)
            file.load_key(password=password)
            file.decrypt(decrypted)
        
        decrypted.seek(0)
        return pd.read_excel(decrypted)

    def _normalize_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Attempts to rename columns to standard names."""
        df.columns = df.columns.astype(str).str.lower().str.strip().str.replace(" ", "_")
        
        rename_map = {}
        for col in df.columns:
            for standard, variations in HEADER_MAPPINGS.items():
                if col in variations:
                    rename_map[col] = standard
                    break
        
        return df.rename(columns=rename_map)

    def parse(self, file_path: str, password: str = None, filename: str = None) -> Tuple[List[Dict[str, Any]], BankDetectionResult]:
        try:
            # Determine loader based on extension or try both
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                try:
                    df = pd.read_excel(file_path)
                except Exception as e:
                     # Check if it's an encrypted file issue
                     if password:
                         try:
                             df = self._decrypt_excel(file_path, password)
                         except Exception as decrypt_err:
                             raise ValueError(f"Decryption failed: {decrypt_err}")
                     else:
                         if "encrypted" in str(e).lower() or "zip" in str(e).lower():
                             raise ValueError("File appears to be encrypted. Please provide a password.") from e
                         raise e
            else:
                try:
                    df = pd.read_csv(file_path)
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='latin1')
                except Exception:
                    try:
                        df = pd.read_excel(file_path)
                    except:
                        raise ValueError("Could not read file as CSV or Excel")

            # Preserve original headers for bank detection before normalizing
            original_headers = list(df.columns.astype(str))

            df = self._normalize_headers(df)
            
            # ─── Bank & Account Detection ───
            # Read the raw file text for additional hints (first 5KB)
            raw_header_text = ""
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_header_text = f.read(5120)
            except Exception:
                pass

            detection = bank_detector.detect(
                filename=filename or file_path,
                headers=original_headers,
                full_text=raw_header_text,
            )

            transactions = []
            
            # Check required columns
            if "date" not in df.columns or ("amount" not in df.columns and ("credit" not in df.columns or "debit" not in df.columns)):
                raise ValueError("Could not detect Date and Amount columns. Please ensure headers are present.")

            for _, row in df.iterrows():
                try:
                    # Date parsing
                    date_str = str(row.get("date"))
                    date_obj = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                    if pd.isna(date_obj):
                        continue 

                    # Amount calculation
                    amount = 0.0
                    if "amount" in df.columns:
                        amt_str = str(row["amount"]).replace(",", "").replace("$", "").replace("₹", "")
                        if "dr" in amt_str.lower():
                            amount = -1 * float(amt_str.lower().replace("dr", ""))
                        elif "cr" in amt_str.lower():
                             amount = float(amt_str.lower().replace("cr", ""))
                        else:
                            try:
                                amount = float(amt_str)
                            except:
                                amount = 0.0
                    elif "credit" in df.columns and "debit" in df.columns:
                        credit_raw = pd.to_numeric(str(row.get("credit", "")).replace(",", ""), errors='coerce')
                        debit_raw = pd.to_numeric(str(row.get("debit", "")).replace(",", ""), errors='coerce')
                        credit = 0.0 if pd.isna(credit_raw) else float(credit_raw)
                        debit = 0.0 if pd.isna(debit_raw) else float(debit_raw)
                        amount = credit - debit

                    # Skip rows with NaN amount
                    if pd.isna(amount):
                        continue
                    
                    # Sanitize description
                    desc = str(row.get("description", "")).strip()
                    if not desc or desc == "nan":
                        desc = "Unknown Transaction"

                    # Sanitize currency
                    cur = str(row.get("currency", "INR")).strip()
                    if not cur or cur == "nan":
                        cur = "INR"

                    # Sanitize reference
                    ref = str(row.get("reference", "")).strip()
                    if ref == "nan":
                        ref = ""

                    txn = {
                        "date": date_obj.to_pydatetime(),
                        "description": desc,
                        "amount": float(amount),
                        "currency": cur,
                        "reference": ref,
                        "raw_data": row.fillna("").to_json()
                    }
                    transactions.append(txn)
                except Exception as e:
                    continue
            
            # If bank wasn't detected from headers/filename, try from transactions
            if not detection.bank_name and transactions:
                txn_detection = bank_detector.detect_from_transactions(transactions)
                if txn_detection.bank_name:
                    detection.bank_name = txn_detection.bank_name
                    detection.bank_code = txn_detection.bank_code
                    detection.confidence = max(detection.confidence, txn_detection.confidence)
                    if not detection.detection_source:
                        detection.detection_source = txn_detection.detection_source

            return transactions, detection

        except Exception as e:
            print(f"CSV Parsing Failed: {e}")
            raise e
