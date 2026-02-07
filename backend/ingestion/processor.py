from typing import List, Dict, Any, Optional, Tuple
from fastapi import UploadFile, HTTPException
import shutil
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

from ingestion.parsers.csv_parser import CSVParser
from ingestion.parsers.pdf_parser import PDFParser
from ingestion.parsers.ollama_vl_parser import OllamaVLParser
from ingestion.enrichment import enrich_transaction
from ingestion.bank_detector import BankDetectionResult
from services.currency import currency_service
from schemas import TransactionCreate


class IngestionProcessor:
    def __init__(self):
        self.csv_parser = CSVParser()
        self.pdf_parser = PDFParser()
        self.vl_parser = OllamaVLParser()

    def _reconcile_transactions(self, std_txns: List[Dict], vl_txns: List[Dict]) -> List[Dict]:
        """Merge deterministic and VL parsed transactions."""
        # 1. Normalize VL transactions to match Standard format (signed amounts)
        normalized_vl = []
        for t in vl_txns:
            amt = t['amount']
            # If VL says expense but amount is positive, flip it
            if t.get('transaction_type') in ['expense', 'debit', 'dr'] and amt > 0:
                amt = -amt
            elif t.get('transaction_type') in ['income', 'credit', 'cr'] and amt < 0:
                amt = abs(amt)
                
            normalized_vl.append({
                'date': t['date'],
                'description': t['description'],
                'amount': amt,
                'currency': t['currency'],
                'reference': t.get('reference', ''),
                'raw_data': t.get('raw_data', {})
            })
            
        if not std_txns:
            return normalized_vl

        # 2. Logic: Start with Standard transactions
        merged = std_txns[:]
        
        # Helper to find match
        def find_match(vl_t, target_list):
            for i, std_t in enumerate(target_list):
                # Match criteria: Amount matches exactly (or close), Date matches (+/- 3 days)
                try:
                    amount_match = abs(std_t['amount'] - vl_t['amount']) < 0.05
                    date_diff = abs((std_t['date'] - vl_t['date']).days)
                    if amount_match and date_diff <= 3:
                        return i
                except:
                    continue
            return -1

        # 3. Merge Flow
        for vt in normalized_vl:
            idx = find_match(vt, merged)
            if idx >= 0:
                # Match found: Enrich
                existing = merged[idx]
                if not isinstance(existing.get('raw_data'), dict):
                    existing['raw_data'] = {'original': existing.get('raw_data')}
                existing['raw_data']['vl_verification'] = 'matched'
            else:
                # No match found: Add VL transaction
                if not isinstance(vt.get('raw_data'), dict):
                     vt['raw_data'] = {}
                vt['raw_data']['source'] = 'vl_only'
                merged.append(vt)
                
        return merged

    async def process_file(
        self,
        file: UploadFile,
        user_id: int,
        password: Optional[str] = None,
        target_currency: str = "INR",
    ) -> Tuple[List[TransactionCreate], Dict[str, Any]]:
        """Process an uploaded file and return enriched transactions + bank detection info."""
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        detection = BankDetectionResult()

        try:
            if suffix.lower() in ['.csv', '.txt']:
                raw_txns, detection = self.csv_parser.parse(tmp_path, password=password, filename=file.filename)
            elif suffix.lower() == '.pdf':
                # 1. Deterministic Parse
                std_txns, std_detect = self.pdf_parser.parse(tmp_path, password=password, filename=file.filename)
                
                # 2. Vision Parse (Always run)
                print(f"[Processor] Running VL extraction for {file.filename}...")
                try:
                    vl_txns, vl_detect = self.vl_parser.parse(tmp_path, password=password)
                except Exception as e:
                    print(f"[Processor] VL Parse failed: {e}")
                    import traceback
                    traceback.print_exc()
                    vl_txns, vl_detect = [], BankDetectionResult()

                # 3. Reconcile
                raw_txns = self._reconcile_transactions(std_txns, vl_txns)
                
                # 4. Merge detection info
                detection = std_detect
                if not detection.bank_name and vl_detect.bank_name:
                    detection.bank_name = vl_detect.bank_name
                if not detection.account_type and vl_detect.account_type:
                    detection.account_type = vl_detect.account_type

            elif suffix.lower() in ['.xlsx', '.xls']:
                raw_txns, detection = self.csv_parser.parse(tmp_path, password=password, filename=file.filename)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format")

            results: List[TransactionCreate] = []
            import math

            for idx, item in enumerate(raw_txns):
                try:
                    amount = item['amount']
                    # Skip NaN amounts
                    if isinstance(amount, float) and (math.isnan(amount) or math.isinf(amount)):
                        continue

                    currency = item.get('currency', 'INR').upper()
                    rate = 1.0
                    amount_converted = amount

                    # Convert to user's target currency
                    if currency != target_currency.upper():
                        try:
                            amount_converted = currency_service.convert(
                                amount, currency, target_currency,
                                date=item.get('date', datetime.now())
                            )
                            rate = amount_converted / amount if amount != 0 else 1.0
                        except Exception as e:
                            print(f"[Processor] Conversion {currency} → {target_currency} failed: {e}")

                    # Enrich transaction with ML-ready metadata
                    enrichment = enrich_transaction(item.get('description', ''), item.get('raw_data'))

                    # Build metadata_json with all extra fields from raw parsing
                    extra_meta = {
                        "parser_currency_detected": currency,
                        "raw_reference": item.get('reference', ''),
                    }
                    if item.get('raw_data'):
                        extra_meta["raw_data"] = item['raw_data'] if isinstance(item['raw_data'], str) else str(item['raw_data'])

                    # Determine transaction type: use enrichment to detect transfers
                    category_hint = enrichment.get('merchant_category', '')
                    if category_hint in ('Own Account Transfer', 'CC Bill Payment'):
                        txn_type = 'transfer'
                    elif category_hint == 'Transfer':
                        txn_type = 'transfer'
                    elif amount_converted > 0:
                        txn_type = 'income'
                    else:
                        txn_type = 'expense'

                    txn = TransactionCreate(
                        user_id=user_id,
                        date=item['date'],
                        description=item['description'],
                        amount=round(amount_converted, 2),
                        currency=target_currency.upper(),
                        transaction_type=txn_type,
                        reference=item.get('reference'),

                        # Original currency data
                        amount_original=round(amount, 2),
                        currency_original=currency,
                        exchange_rate=round(rate, 6),
                        source="file",
                        source_file=file.filename,
                        raw_data=str(item.get('raw_data', {})),

                        # Enriched metadata
                        merchant_name=enrichment.get('merchant_name'),
                        merchant_category=enrichment.get('merchant_category'),
                        transaction_method=enrichment.get('transaction_method'),
                        location=enrichment.get('location'),
                        card_last_four=enrichment.get('card_last_four'),
                        metadata_json=json.dumps(extra_meta),
                    )
                    results.append(txn)
                except Exception as e:
                    print(f"[Processor] Skipping txn #{idx}: {e} | raw={item}")
                    continue

            # Build detection info dict
            detection_info = detection.to_dict()
            detection_info["transaction_count"] = len(results)

            return results, detection_info

        finally:
            # Clean up temp file — retry on Windows where file handles may linger
            self._safe_remove(tmp_path)

    @staticmethod
    def _safe_remove(path: str, retries: int = 3, delay: float = 0.3):
        """Remove a file with retries for Windows file-locking issues."""
        import time
        import gc
        for attempt in range(retries):
            try:
                if os.path.exists(path):
                    gc.collect()  # Help release any lingering file handles
                    os.remove(path)
                return
            except PermissionError:
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    print(f"[Processor] WARNING: Could not delete temp file {path} (file in use)")
            except Exception:
                return

processor = IngestionProcessor()
