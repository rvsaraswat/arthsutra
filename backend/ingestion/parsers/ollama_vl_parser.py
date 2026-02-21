import json
import base64
import httpx
import pypdfium2 as pdfium
from typing import List, Dict, Any, Tuple
from datetime import datetime
import re
from ..bank_detector import BankDetectionResult

class OllamaVLParser:
    def __init__(self, model_name: str = "qwen2.5-vl:7b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        self._available: bool | None = None  # Cache availability check

    def _render_pages_to_base64(self, file_path: str, max_pages: int = 5) -> List[str]:
        """Convert first N pages of PDF to base64 encoded PNG images."""
        images_b64 = []
        pdf = None
        try:
            pdf = pdfium.PdfDocument(file_path)
            n_pages = min(len(pdf), max_pages)
            
            for i in range(n_pages):
                page = pdf[i]
                # Render at 200 DPI (scale=3 roughly for 72dpi base)
                bitmap = page.render(scale=3)
                pil_image = bitmap.to_pil()
                
                # Convert to bytes
                import io
                buffered = io.BytesIO()
                pil_image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                images_b64.append(img_str)
                
            return images_b64
        except Exception as e:
            print(f"[VL Parser] Error rendering PDF: {e}")
            return []
        finally:
            # Explicitly close the PDF to release the file handle (critical on Windows)
            if pdf is not None:
                try:
                    pdf.close()
                except Exception:
                    pass

    def _clean_json_response(self, text: str) -> str:
        """Extract JSON from potential markdown code blocks."""
        # Try to find JSON block
        match = re.search(r'```json\s*(\{.*\}|\[.*\])\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
        
        match = re.search(r'```\s*(\{.*\}|\[.*\])\s*```', text, re.DOTALL)
        if match:
            return match.group(1)
            
        return text

    def _is_ollama_available(self) -> bool:
        """Quick check if Ollama is reachable. Cached after first check."""
        if self._available is not None:
            return self._available
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            self._available = r.status_code == 200
        except Exception:
            self._available = False
        if not self._available:
            print("[VL Parser] Ollama not available, skipping VL extraction")
        return self._available

    def parse(self, file_path: str, password: str = None) -> Tuple[List[Dict[str, Any]], BankDetectionResult]:
        """
        Parse PDF using Visual Language Model.
        Returns generic transaction list and bank detection info.
        """
        # Quick check — skip VL entirely if Ollama isn't running
        if not self._is_ollama_available():
            return [], BankDetectionResult()
        
        images = self._render_pages_to_base64(file_path)
        if not images:
            return [], BankDetectionResult()

        transactions = []
        detected_bank = None
        
        prompt = """
        You are a financial data extraction AI. Extract the bank statement transactions from this image.
        
        Return STRICT JSON format only. No markdown formatting, no conversational text.
        
        Output Structure:
        {
            "bank_name": "Name of the bank detected (or null)",
            "account_type": "credit_card | savings | current (or null)",
            "currency": "Currency code (INR, USD, QAR, etc)",
            "transactions": [
                {
                    "date": "DD/MM/YYYY",
                    "description": "Full transaction description",
                    "amount": 100.50 (positive number),
                    "type": "credit (income/payment) | debit (expense)",
                    "category_hint": "Food | Travel | etc (optional)"
                }
            ]
        }
        
        Rules:
        1. Extract Date in DD/MM/YYYY format. If year is missing, assume current year.
        2. Amount must be absolute float value. Use 'type' to indicate direction.
        3. If multiple items exist, list them all.
        4. Ignoring running balance columns.
        """

        # We process pages in batches or one by one?
        # VLLMs context window might be full with too many images. 
        # Better to do page by page or small batches.
        # qwen2.5-vl supports multi-image but let's be safe: 1 request per page.
        
        full_txns = []
        
        for i, img in enumerate(images):
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "images": [img],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temp for deterministic output
                        "num_ctx": 4096
                    }
                }
                
                # print(f"[VL Parser] Processing page {i+1}...")
                response = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=60.0)
                response.raise_for_status()
                
                result = response.json()
                raw_text = result.get('response', '')
                cleaned_json = self._clean_json_response(raw_text)
                
                try:
                    data = json.loads(cleaned_json)
                    
                    # Extract bank info from first page only
                    if i == 0:
                        detected_bank = data.get('bank_name')
                        
                    page_txns = data.get('transactions', [])
                    
                    # Normalize transactions
                    for t in page_txns:
                        # Normalize date
                        try:
                            # Try DD/MM/YYYY
                            d_str = t.get('date', '')
                            # Basic cleanup
                            d_str = d_str.replace('-', '/').replace('.', '/')
                            parsed_date = datetime.strptime(d_str, "%d/%m/%Y")
                        except:
                            try:
                                # Try MM/DD/YYYY fallback
                                parsed_date = datetime.strptime(d_str, "%m/%d/%Y")
                            except:
                                parsed_date = datetime.now() # Fallback
                        
                        # Normalize amount (handling sign based on type)
                        amt = float(t.get('amount', 0))
                        is_expense = t.get('type', '').lower() in ['debit', 'expense', 'dr']
                        
                        # In the main app, we often use signed amounts (neg = expense) or separate type
                        # The app seems to standardize on signed amounts for 'amount' field often, 
                        # but check Schema: TransactionCreate uses (amount, type).
                        # Let's keep it consistent with Dict output of valid parser
                        
                        full_txns.append({
                            "date": parsed_date,
                            "description": t.get('description', ''),
                            "amount": amt,
                            "transaction_type": "expense" if is_expense else "income",
                            "currency": data.get('currency', 'INR'),
                            "reference": "", # generated or empty
                            "raw_data": t # keep original VL extraction
                        })
                        
                except json.JSONDecodeError:
                    print(f"[VL Parser] Page {i+1} returned invalid JSON: {raw_text[:100]}...")
                    continue
                    
            except Exception as e:
                print(f"[VL Parser] Error processing page {i+1}: {e}")
                continue

        # Build BankDetectionResult
        detection_result = BankDetectionResult()
        if detected_bank:
            detection_result.bank_name = detected_bank
            detection_result.confidence = 0.8  # VL is usually good at reading headers
        
        return full_txns, detection_result
