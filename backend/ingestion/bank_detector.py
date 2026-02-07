"""
Bank & Account Type Detection Engine.

Identifies the bank/institution and account type (savings, current, credit card, etc.)
from:
    1. Filename patterns
    2. CSV / Excel column headers
    3. PDF full-text content (logos, addresses, headers)
    4. Transaction descriptions (bank-specific references)

Supports:
    - Indian banks (SBI, HDFC, ICICI, Axis, Kotak, PNB, BOB, Canara, IndusInd, Yes, IDFC, etc.)
    - International banks (Chase, Citi, AMEX, Barclays, HSBC, Standard Chartered, DBS, etc.)
    - Gulf banks (QNB, NBK, FAB, Emirates NBD, Mashreq, etc.)
    - Digital wallets / neobanks (Paytm, Fi, Jupiter, Niyo, etc.)
"""

import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class BankDetectionResult:
    """Result from bank & account detection."""
    bank_name: Optional[str] = None          # e.g. "HDFC Bank"
    bank_code: Optional[str] = None          # e.g. "HDFC"
    account_type: Optional[str] = None       # One of ACCOUNT_TYPES from models.py
    account_type_label: Optional[str] = None # e.g. "Savings Account"
    confidence: float = 0.0                  # 0.0 – 1.0
    detection_source: Optional[str] = None   # "filename", "headers", "pdf_text", "transactions"

    def to_dict(self) -> dict:
        return {
            "bank_name": self.bank_name,
            "bank_code": self.bank_code,
            "account_type": self.account_type,
            "account_type_label": self.account_type_label,
            "confidence": round(self.confidence, 2),
            "detection_source": self.detection_source,
        }


# ──────────────────────────────────────────────
# Bank fingerprints — patterns unique to each bank
# ──────────────────────────────────────────────

BANK_FINGERPRINTS = [
    # ─── Indian Banks ───
    {
        "name": "State Bank of India",
        "code": "SBI",
        "patterns": [
            r'\bSBI\b', r'\bSTATE\s*BANK\s*OF\s*INDIA\b', r'\bSBIN\b',
            r'\bSTATE\s*BANK\b', r'\bSBI\s*YONO\b',
        ],
        "header_hints": ["sbi", "state bank"],
    },
    {
        "name": "HDFC Bank",
        "code": "HDFC",
        "patterns": [
            r'\bHDFC\s*BANK\b', r'\bHDFC\b(?!\s*LIFE|\s*ERGO|\s*AMC|\s*MUTUAL)',
            r'\bHDFC\s*LTD\b', r'\bNET\s*BANKING\s*HDFC\b',
        ],
        "header_hints": ["hdfc"],
    },
    {
        "name": "ICICI Bank",
        "code": "ICICI",
        "patterns": [
            r'\bICICI\s*BANK\b', r'\bICICI\b(?!\s*PRUDENTIAL|\s*LOMBARD|\s*DIRECT)',
        ],
        "header_hints": ["icici"],
    },
    {
        "name": "Axis Bank",
        "code": "AXIS",
        "patterns": [
            r'\bAXIS\s*BANK\b', r'\bAXIS\b(?!\s*AMC|\s*MUTUAL)',
        ],
        "header_hints": ["axis"],
    },
    {
        "name": "Kotak Mahindra Bank",
        "code": "KOTAK",
        "patterns": [
            r'\bKOTAK\s*MAHINDRA\b', r'\bKOTAK\s*BANK\b', r'\bKOTAK\b',
        ],
        "header_hints": ["kotak"],
    },
    {
        "name": "Punjab National Bank",
        "code": "PNB",
        "patterns": [
            r'\bPUNJAB\s*NATIONAL\s*BANK\b', r'\bPNB\b',
        ],
        "header_hints": ["pnb", "punjab national"],
    },
    {
        "name": "Bank of Baroda",
        "code": "BOB",
        "patterns": [
            r'\bBANK\s*OF\s*BARODA\b', r'\bBOB\b',
        ],
        "header_hints": ["baroda", "bob"],
    },
    {
        "name": "Canara Bank",
        "code": "CANARA",
        "patterns": [
            r'\bCANARA\s*BANK\b', r'\bCANARA\b',
        ],
        "header_hints": ["canara"],
    },
    {
        "name": "IndusInd Bank",
        "code": "INDUSIND",
        "patterns": [
            r'\bINDUSIND\s*BANK\b', r'\bINDUSIND\b',
        ],
        "header_hints": ["indusind"],
    },
    {
        "name": "Yes Bank",
        "code": "YES",
        "patterns": [
            r'\bYES\s*BANK\b',
        ],
        "header_hints": ["yes bank"],
    },
    {
        "name": "IDFC First Bank",
        "code": "IDFC",
        "patterns": [
            r'\bIDFC\s*FIRST\b', r'\bIDFC\s*BANK\b', r'\bIDFC\b',
        ],
        "header_hints": ["idfc"],
    },
    {
        "name": "Union Bank of India",
        "code": "UNION",
        "patterns": [
            r'\bUNION\s*BANK\s*OF\s*INDIA\b', r'\bUNION\s*BANK\b',
        ],
        "header_hints": ["union bank"],
    },
    {
        "name": "Bank of India",
        "code": "BOI",
        "patterns": [
            r'\bBANK\s*OF\s*INDIA\b(?!\s*BARODA)',
        ],
        "header_hints": ["bank of india"],
    },
    {
        "name": "Indian Bank",
        "code": "INDIAN",
        "patterns": [
            r'\bINDIAN\s*BANK\b',
        ],
        "header_hints": ["indian bank"],
    },
    {
        "name": "Federal Bank",
        "code": "FEDERAL",
        "patterns": [
            r'\bFEDERAL\s*BANK\b',
        ],
        "header_hints": ["federal bank"],
    },
    {
        "name": "South Indian Bank",
        "code": "SIB",
        "patterns": [
            r'\bSOUTH\s*INDIAN\s*BANK\b',
        ],
        "header_hints": ["south indian"],
    },
    {
        "name": "RBL Bank",
        "code": "RBL",
        "patterns": [
            r'\bRBL\s*BANK\b', r'\bRATNAKAR\b',
        ],
        "header_hints": ["rbl"],
    },
    {
        "name": "Bandhan Bank",
        "code": "BANDHAN",
        "patterns": [
            r'\bBANDHAN\s*BANK\b', r'\bBANDHAN\b',
        ],
        "header_hints": ["bandhan"],
    },

    # ─── International Banks ───
    {
        "name": "JPMorgan Chase",
        "code": "CHASE",
        "patterns": [
            r'\bCHASE\b', r'\bJPMORGAN\b', r'\bJ\.?P\.?\s*MORGAN\b',
        ],
        "header_hints": ["chase", "jpmorgan"],
    },
    {
        "name": "Citibank",
        "code": "CITI",
        "patterns": [
            r'\bCITIBANK\b', r'\bCITI\s*BANK\b', r'\bCITI\b',
        ],
        "header_hints": ["citi"],
    },
    {
        "name": "American Express",
        "code": "AMEX",
        "patterns": [
            r'\bAMERICAN\s*EXPRESS\b', r'\bAMEX\b',
        ],
        "header_hints": ["amex", "american express"],
    },
    {
        "name": "HSBC",
        "code": "HSBC",
        "patterns": [
            r'\bHSBC\b', r'\bHONGKONG\s*AND\s*SHANGHAI\b',
        ],
        "header_hints": ["hsbc"],
    },
    {
        "name": "Standard Chartered",
        "code": "SC",
        "patterns": [
            r'\bSTANDARD\s*CHARTERED\b', r'\bSTAN\s*CHART\b',
        ],
        "header_hints": ["standard chartered"],
    },
    {
        "name": "Barclays",
        "code": "BARCLAYS",
        "patterns": [
            r'\bBARCLAYS\b',
        ],
        "header_hints": ["barclays"],
    },
    {
        "name": "Bank of America",
        "code": "BOA",
        "patterns": [
            r'\bBANK\s*OF\s*AMERICA\b', r'\bBOFA\b',
        ],
        "header_hints": ["bank of america"],
    },
    {
        "name": "Wells Fargo",
        "code": "WELLSFARGO",
        "patterns": [
            r'\bWELLS\s*FARGO\b',
        ],
        "header_hints": ["wells fargo"],
    },
    {
        "name": "DBS Bank",
        "code": "DBS",
        "patterns": [
            r'\bDBS\s*BANK\b', r'\bDBS\b',
        ],
        "header_hints": ["dbs"],
    },
    {
        "name": "Deutsche Bank",
        "code": "DEUTSCHE",
        "patterns": [
            r'\bDEUTSCHE\s*BANK\b',
        ],
        "header_hints": ["deutsche"],
    },

    # ─── Gulf Banks ───
    {
        "name": "Qatar National Bank",
        "code": "QNB",
        "patterns": [
            r'\bQNB\b', r'\bQATAR\s*NATIONAL\s*BANK\b',
        ],
        "header_hints": ["qnb"],
    },
    {
        "name": "Emirates NBD",
        "code": "ENBD",
        "patterns": [
            r'\bEMIRATES\s*NBD\b', r'\bENBD\b',
        ],
        "header_hints": ["emirates nbd"],
    },
    {
        "name": "First Abu Dhabi Bank",
        "code": "FAB",
        "patterns": [
            r'\bFIRST\s*ABU\s*DHABI\b', r'\bFAB\b(?!\s*RIC)',
        ],
        "header_hints": ["fab", "first abu dhabi"],
    },
    {
        "name": "Mashreq Bank",
        "code": "MASHREQ",
        "patterns": [
            r'\bMASHREQ\b',
        ],
        "header_hints": ["mashreq"],
    },
    {
        "name": "National Bank of Kuwait",
        "code": "NBK",
        "patterns": [
            r'\bNBK\b', r'\bNATIONAL\s*BANK\s*OF\s*KUWAIT\b',
        ],
        "header_hints": ["nbk"],
    },
    {
        "name": "Al Rajhi Bank",
        "code": "ALRAJHI",
        "patterns": [
            r'\bAL\s*RAJHI\b', r'\bRAJHI\b',
        ],
        "header_hints": ["rajhi"],
    },
    {
        "name": "Saudi National Bank",
        "code": "SNB",
        "patterns": [
            r'\bSAUDI\s*NATIONAL\s*BANK\b', r'\bSNB\b', r'\bSAMBA\b',
        ],
        "header_hints": ["snb", "saudi national"],
    },
    {
        "name": "Commercial Bank of Qatar",
        "code": "CBQ",
        "patterns": [
            r'\bCOMMERCIAL\s*BANK\b(?:\s*OF\s*QATAR)?', r'\bCBQ\b',
            r'\bCOMMERCIAL\s*BANK\s*P\.?S\.?Q\.?S\.?', r'\bCOMMERCIAL\s*BANK\s*Q\.?P\.?S\.?C',
            r'\bCOMMERCIAL\s*BANK\s*(?:PS|QSC|QPSC)\b',
        ],
        "header_hints": ["cbq", "commercial bank"],
    },
    {
        "name": "Doha Bank",
        "code": "DOHA",
        "patterns": [
            r'\bDOHA\s*BANK\b',
        ],
        "header_hints": ["doha bank"],
    },
    {
        "name": "Qatar Islamic Bank",
        "code": "QIB",
        "patterns": [
            r'\bQATAR\s*ISLAMIC\s*BANK\b', r'\bQIB\b',
        ],
        "header_hints": ["qib", "qatar islamic"],
    },
    {
        "name": "Ahli Bank Qatar",
        "code": "AHLI",
        "patterns": [
            r'\bAHLI\s*BANK\b', r'\bAL\s*AHLI\s*BANK\b',
        ],
        "header_hints": ["ahli"],
    },

    # ─── Neobanks / Digital ───
    {
        "name": "Paytm Payments Bank",
        "code": "PAYTM",
        "patterns": [
            r'\bPAYTM\b', r'\bPAYTM\s*PAYMENTS\b',
        ],
        "header_hints": ["paytm"],
    },
    {
        "name": "Fi Money",
        "code": "FI",
        "patterns": [
            r'\bFI\s*MONEY\b', r'\bFI\.\s*MONEY\b',
        ],
        "header_hints": ["fi money"],
    },
    {
        "name": "Jupiter",
        "code": "JUPITER",
        "patterns": [
            r'\bJUPITER\b(?!\s*PLANET)',
        ],
        "header_hints": ["jupiter"],
    },
    {
        "name": "Niyo",
        "code": "NIYO",
        "patterns": [
            r'\bNIYO\b',
        ],
        "header_hints": ["niyo"],
    },
    {
        "name": "Revolut",
        "code": "REVOLUT",
        "patterns": [
            r'\bREVOLUT\b',
        ],
        "header_hints": ["revolut"],
    },
    {
        "name": "Wise",
        "code": "WISE",
        "patterns": [
            r'\bWISE\b(?!\s*LY)', r'\bTRANSFERWISE\b',
        ],
        "header_hints": ["wise", "transferwise"],
    },
]

# ──────────────────────────────────────────────
# Account-type detection patterns
# ──────────────────────────────────────────────

ACCOUNT_TYPE_PATTERNS = [
    # Credit cards (check first - highest priority)
    {
        "type": "credit_card",
        "label": "Credit Card",
        "patterns": [
            r'\bCREDIT\s*CARD\b', r'\bCC\s*STATEMENT\b', r'\bCARD\s*STATEMENT\b',
            r'\bVISA\s*(PLATINUM|GOLD|SIGNATURE|INFINITE|CLASSIC)\b',
            r'\bMASTERCARD\s*(WORLD|PLATINUM|GOLD|TITANIUM)\b',
            r'\bRUPAY\b.*\bCARD\b', r'\bDINERS\s*CLUB\b',
            r'\bAMEX\b.*\b(CARD|MEMBER)\b',
            r'\bMINIMUM\s*(DUE|PAYMENT)\b', r'\bCREDIT\s*LIMIT\b',
            r'\bPAYMENT\s*DUE\s*DATE\b', r'\bOUTSTANDING\s*BALANCE\b',
            r'\bSTATEMENT\s*OF\s*ACCOUNT.*CARD\b',
            r'\bBILLING\s*CYCLE\b', r'\bREWARD\s*POINTS?\b',
        ],
    },
    # Current / checking
    {
        "type": "current",
        "label": "Current Account",
        "patterns": [
            r'\bCURRENT\s*ACCOUNT\b', r'\bCHECKING\s*ACCOUNT\b',
            r'\bCURRENT\s*A/?C\b', r'\bCA\s*STATEMENT\b',
            r'\bBUSINESS\s*ACCOUNT\b', r'\bCORPORATE\s*ACCOUNT\b',
        ],
    },
    # NRO
    {
        "type": "NRO",
        "label": "NRO Account",
        "patterns": [
            r'\bNRO\b', r'\bNON[\s\-]*RESIDENT\s*ORDINARY\b',
        ],
    },
    # NRE
    {
        "type": "NRE",
        "label": "NRE Account",
        "patterns": [
            r'\bNRE\b', r'\bNON[\s\-]*RESIDENT\s*EXTERNAL\b',
        ],
    },
    # Salary account
    {
        "type": "salary",
        "label": "Salary Account",
        "patterns": [
            r'\bSALARY\s*ACCOUNT\b', r'\bSALARY\s*A/?C\b',
            r'\bPAYROLL\s*ACCOUNT\b',
        ],
    },
    # FD
    {
        "type": "FD",
        "label": "Fixed Deposit",
        "patterns": [
            r'\bFIXED\s*DEPOSIT\b', r'\bFD\s*STATEMENT\b',
            r'\bTERM\s*DEPOSIT\b',
        ],
    },
    # RD
    {
        "type": "RD",
        "label": "Recurring Deposit",
        "patterns": [
            r'\bRECURRING\s*DEPOSIT\b', r'\bRD\s*STATEMENT\b',
        ],
    },
    # PPF
    {
        "type": "PPF",
        "label": "PPF Account",
        "patterns": [
            r'\bPPF\b', r'\bPUBLIC\s*PROVIDENT\s*FUND\b',
        ],
    },
    # Investment / Demat
    {
        "type": "stocks",
        "label": "Demat / Trading Account",
        "patterns": [
            r'\bDEMAT\b', r'\bTRADING\s*ACCOUNT\b',
            r'\bZERODHA\b', r'\bGROWW\b', r'\bUPSTOX\b',
            r'\bCONTRACT\s*NOTE\b', r'\bSETTLEMENT\b.*\bTRADE\b',
        ],
    },
    # Wallet
    {
        "type": "wallet",
        "label": "Digital Wallet",
        "patterns": [
            r'\bWALLET\b', r'\bPREPAID\b', r'\bPAYTM\s*WALLET\b',
            r'\bPHONEPE\s*WALLET\b', r'\bGOOGLE\s*PAY\b',
        ],
    },
    # Overdraft
    {
        "type": "overdraft",
        "label": "Overdraft Account",
        "patterns": [
            r'\bOVERDRAFT\b', r'\bOD\s*ACCOUNT\b', r'\bOD\s*A/?C\b',
        ],
    },
    # Savings (last - default fallback for bank statements)
    {
        "type": "savings",
        "label": "Savings Account",
        "patterns": [
            r'\bSAVINGS?\s*ACCOUNT\b', r'\bSAVINGS?\s*A/?C\b',
            r'\bSB\s*ACCOUNT\b', r'\bSA\s*STATEMENT\b',
            r'\bSAVINGS?\s*BANK\b',
        ],
    },
]


# ──────────────────────────────────────────────
# Main detection class
# ──────────────────────────────────────────────

class BankDetector:
    """Detects bank and account type from various sources."""

    def detect_from_filename(self, filename: str) -> BankDetectionResult:
        """Detect bank & account type from the file name."""
        if not filename:
            return BankDetectionResult()

        name_upper = filename.upper()
        result = BankDetectionResult(detection_source="filename")

        # Try bank detection
        for bank in BANK_FINGERPRINTS:
            for pattern in bank["patterns"]:
                if re.search(pattern, name_upper):
                    result.bank_name = bank["name"]
                    result.bank_code = bank["code"]
                    result.confidence = 0.7
                    break
            if result.bank_name:
                break

        # Try account type detection
        for acct in ACCOUNT_TYPE_PATTERNS:
            for pattern in acct["patterns"]:
                if re.search(pattern, name_upper):
                    result.account_type = acct["type"]
                    result.account_type_label = acct["label"]
                    result.confidence = max(result.confidence, 0.6)
                    break
            if result.account_type:
                break

        return result

    def detect_from_headers(self, headers: list) -> BankDetectionResult:
        """Detect bank from CSV / Excel column header names."""
        if not headers:
            return BankDetectionResult()

        headers_lower = " ".join(str(h).lower() for h in headers)
        result = BankDetectionResult(detection_source="headers")

        for bank in BANK_FINGERPRINTS:
            for hint in bank.get("header_hints", []):
                if hint in headers_lower:
                    result.bank_name = bank["name"]
                    result.bank_code = bank["code"]
                    result.confidence = 0.5
                    break
            if result.bank_name:
                break

        return result

    def detect_from_text(self, text: str) -> BankDetectionResult:
        """Detect bank & account type from full text (PDF page text, etc.)."""
        if not text:
            return BankDetectionResult()

        text_upper = text.upper()
        # Extract first 500 chars as "header area" for extra weighting
        header_area = text_upper[:500]
        result = BankDetectionResult(detection_source="pdf_text")

        # Bank detection — uses combined scoring:
        #   distinct_patterns: how many different patterns match (breadth)
        #   frequency: total number of occurrences across all patterns (depth)
        #   header_bonus: extra weight if patterns match in header area (first 500 chars)
        best_bank_score = 0
        for bank in BANK_FINGERPRINTS:
            distinct_patterns = 0
            frequency = 0
            header_bonus = 0
            for pattern in bank["patterns"]:
                matches = re.findall(pattern, text_upper)
                if matches:
                    distinct_patterns += 1
                    frequency += len(matches)
                    # Check if pattern also matches in header area
                    if re.search(pattern, header_area):
                        header_bonus += 2  # Header matches worth more
            # Score: distinct patterns × 10 + frequency + header bonus
            score = distinct_patterns * 10 + frequency + header_bonus
            if score > best_bank_score:
                best_bank_score = score
                result.bank_name = bank["name"]
                result.bank_code = bank["code"]
                result.confidence = min(0.5 + distinct_patterns * 0.15, 0.95)

        # Account type detection
        for acct in ACCOUNT_TYPE_PATTERNS:
            found = False
            for pattern in acct["patterns"]:
                if re.search(pattern, text_upper):
                    result.account_type = acct["type"]
                    result.account_type_label = acct["label"]
                    result.confidence = max(result.confidence, 0.7)
                    found = True
                    break
            if found:
                break

        # Heuristic: if we detected a bank but not account type, and the text
        # looks like a bank statement, default to savings
        if result.bank_name and not result.account_type:
            # Check for common bank statement keywords
            if re.search(r'\b(STATEMENT|LEDGER|PASSBOOK|ACCOUNT\s*SUMMARY)\b', text_upper):
                result.account_type = "savings"
                result.account_type_label = "Savings Account"
                result.confidence = max(result.confidence, 0.4)

        return result

    def detect_from_transactions(self, transactions: list) -> BankDetectionResult:
        """Detect bank from transaction descriptions (batch)."""
        if not transactions:
            return BankDetectionResult()

        # Combine all descriptions
        all_descs = " ".join(
            str(t.get("description", "")) for t in transactions[:50]  # sample first 50
        ).upper()

        result = BankDetectionResult(detection_source="transactions")

        best_bank_score = 0
        for bank in BANK_FINGERPRINTS:
            match_count = 0
            for pattern in bank["patterns"]:
                matches = re.findall(pattern, all_descs)
                match_count += len(matches)
            if match_count > best_bank_score and match_count >= 2:
                best_bank_score = match_count
                result.bank_name = bank["name"]
                result.bank_code = bank["code"]
                result.confidence = min(0.3 + match_count * 0.05, 0.7)

        return result

    def detect(
        self,
        filename: str = None,
        headers: list = None,
        full_text: str = None,
        transactions: list = None,
    ) -> BankDetectionResult:
        """
        Run all detection strategies and merge results.
        Priority: pdf_text > filename > headers > transactions
        """
        candidates = []

        if full_text:
            r = self.detect_from_text(full_text)
            if r.bank_name or r.account_type:
                candidates.append(r)

        if filename:
            r = self.detect_from_filename(filename)
            if r.bank_name or r.account_type:
                candidates.append(r)

        if headers:
            r = self.detect_from_headers(headers)
            if r.bank_name or r.account_type:
                candidates.append(r)

        if transactions:
            r = self.detect_from_transactions(transactions)
            if r.bank_name or r.account_type:
                candidates.append(r)

        if not candidates:
            return BankDetectionResult()

        # Pick the best overall result by merging
        # Use highest-confidence bank detection
        best = BankDetectionResult()

        # Get best bank
        bank_candidates = [c for c in candidates if c.bank_name]
        if bank_candidates:
            top = max(bank_candidates, key=lambda c: c.confidence)
            best.bank_name = top.bank_name
            best.bank_code = top.bank_code
            best.confidence = top.confidence
            best.detection_source = top.detection_source

        # Get best account type
        acct_candidates = [c for c in candidates if c.account_type]
        if acct_candidates:
            top = max(acct_candidates, key=lambda c: c.confidence)
            best.account_type = top.account_type
            best.account_type_label = top.account_type_label
            best.confidence = max(best.confidence, top.confidence)
            if not best.detection_source:
                best.detection_source = top.detection_source

        return best


# Singleton
bank_detector = BankDetector()
