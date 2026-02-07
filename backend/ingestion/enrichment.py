"""
Transaction Enrichment Engine.

Extracts rich metadata from raw transaction descriptions for ML categorization:
- merchant_name: cleaned payee / merchant name
- transaction_method: POS, ATM, UPI, NEFT, IMPS, WIRE, ACH, ONLINE, AUTOPAY, CHECK, etc.
- location: city / country if present
- card_last_four: last 4 digits of card if present
- merchant_category: high-level category hint
"""

import re
from typing import Dict, Any, Optional


# ---------- Transaction method patterns ----------

_METHOD_PATTERNS = [
    # Indian payment methods
    (r'\bUPI\b', 'UPI'),
    (r'\bNEFT\b', 'NEFT'),
    (r'\bRTGS\b', 'RTGS'),
    (r'\bIMPS\b', 'IMPS'),
    (r'\bNACH\b', 'AUTOPAY'),
    (r'\bECS\b', 'AUTOPAY'),
    (r'\bAUTO[\s\-]?PAY\b', 'AUTOPAY'),
    (r'\bSI[\s\-]?PAYMENT\b', 'AUTOPAY'),  # Standing instruction
    (r'\bATM\b', 'ATM'),
    (r'\bCASH\s*WITHDRAWAL\b', 'ATM'),
    (r'\bCASH\s*DEPOSIT\b', 'CASH'),
    (r'\bCHQ\b|\bCHEQUE\b|\bCHECK\b', 'CHECK'),
    (r'\bDD\b.*CLEARING', 'CHECK'),

    # International payment methods
    (r'\bPOS\b|\bP\.O\.S\b', 'POS'),
    (r'\bSWIPE\b|\bCARD\s*PURCHASE\b', 'POS'),
    (r'\bEFTPOS\b', 'POS'),
    (r'\bPAYPAL\b', 'ONLINE'),
    (r'\bSTRIPE\b', 'ONLINE'),
    (r'\bWIRE\s*TRANSFER\b', 'WIRE'),
    (r'\bSWIFT\b', 'WIRE'),
    (r'\bACH\b', 'ACH'),
    (r'\bDIRECT\s*DEBIT\b', 'AUTOPAY'),
    (r'\bDIRECT\s*DEPOSIT\b', 'ACH'),
    (r'\bONLINE\b.*\b(TRANSFER|PAYMENT|TXN)\b', 'ONLINE'),
    (r'\bMOBILE\s*(BANKING|PAYMENT)\b', 'MOBILE'),
    (r'\bINT\'?L\s*PURCHASE\b', 'POS'),
    (r'\bMERCHANT\s*PAYMENT\b', 'POS'),
    (r'\bE[\s\-]?COMMERCE\b', 'ONLINE'),
    (r'\bDEBIT\s*CARD\b', 'POS'),
    (r'\bCREDIT\s*CARD\b', 'POS'),
]

# ---------- Card number patterns ----------

_CARD_PATTERNS = [
    r'(?:CARD|CC|ACCT)\s*(?:NO|#|NUMBER)?\s*[\.\-\*]*\s*(\d{4})\b',
    r'X{4,}[\-\s]*(\d{4})\b',       # XXXX-XXXX-1234
    r'\*{4,}[\-\s]*(\d{4})\b',      # ****1234
    r'(?:ENDING|LAST)\s*(?:IN\s+)?(\d{4})\b',
    r'(?:CARD)\s+(\d{4})\b',
]

# ---------- Location extraction patterns ----------

_LOCATION_PATTERNS = [
    # City, State/Country patterns
    r'(?:AT|IN|@)\s+(.{3,40}?)\s*(?:ON\s+\d|$)',
    # US format: MERCHANT NAME    CITY   ST
    r'\s{2,}([A-Z][A-Za-z\s]{2,20})\s+([A-Z]{2})\s*$',
    # Country codes at end
    r'\s+(US|UK|IN|QA|AE|SA|SG|HK|AU|CA|DE|FR|JP|CN|KR|TH|MY|PH|ID|NZ)\s*$',
]

# ---------- Category hint patterns ----------

_CATEGORY_HINTS = [
    # Food & Dining
    (r'\b(RESTAURANT|CAFE|COFFEE|PIZZA|BURGER|DINER|FOOD|MCDONALD|STARBUCKS|SUBWAY|KFC|DOMINOS|ZOMATO|SWIGGY|UBER\s*EATS|DELIVEROO|GRUBHUB)\b', 'Food & Dining'),
    # Groceries
    (r'\b(GROCERY|SUPERMARKET|WALMART|TARGET|COSTCO|TESCO|ALDI|LIDL|CARREFOUR|BIGBASKET|DMART|RELIANCE\s*FRESH|WHOLE\s*FOODS|TRADER\s*JOE)\b', 'Groceries'),
    # Transport
    (r'\b(UBER|LYFT|OLA|RAPIDO|GRAB|GOJEK|TAXI|CAB|METRO|TRANSIT|BUS|RAILWAY|IRCTC|AIRLINE|FLIGHT|EMIRATES|INDIGO|SPICEJET|AIR\s*INDIA)\b', 'Transport'),
    # Fuel
    (r'\b(PETROL|DIESEL|GAS\s*STATION|FUEL|SHELL|BP|INDIAN\s*OIL|HP\s*PETROL|BHARAT\s*PETROL|ARAMCO|TOTAL|CHEVRON|EXXON)\b', 'Fuel'),
    # Shopping
    (r'\b(AMAZON|FLIPKART|EBAY|ALIEXPRESS|MYNTRA|AJIO|ZARA|H&M|NIKE|ADIDAS|APPLE\s*STORE|BEST\s*BUY|IKEA)\b', 'Shopping'),
    # Utilities
    (r'\b(ELECTRICITY|WATER\s*BILL|GAS\s*BILL|UTILITY|ELECTRIC|POWER|TELECOM|AIRTEL|JIO|VODAFONE|INTERNET|BROADBAND|WIFI|PHONE\s*BILL)\b', 'Utilities'),
    # Subscriptions
    (r'\b(NETFLIX|SPOTIFY|PRIME|DISNEY|YOUTUBE|APPLE\s*MUSIC|HULU|HBO|SUBSCRIPTION|MEMBERSHIP|ANNUAL\s*FEE|MONTHLY\s*FEE)\b', 'Subscriptions'),
    # Healthcare
    (r'\b(HOSPITAL|CLINIC|PHARMACY|MEDICAL|DOCTOR|DENTAL|HEALTH|APOLLO|FORTIS|MAX\s*HOSPITAL|CVS|WALGREEN)\b', 'Healthcare'),
    # Insurance
    (r'\b(INSURANCE|LIC|PREMIUM|POLICY|HEALTH\s*INS|LIFE\s*INS|MOTOR\s*INS|HDFC\s*LIFE|ICICI\s*LOMBARD|GEICO|ALLSTATE)\b', 'Insurance'),
    # Education
    (r'\b(SCHOOL|COLLEGE|UNIVERSITY|TUITION|EDUCATION|COURSERA|UDEMY|SKILLSHARE|EXAM\s*FEE)\b', 'Education'),
    # Rent & Housing
    (r'\b(RENT|LEASE|HOUSING|MORTGAGE|HOME\s*LOAN|EMI)\b', 'Rent & Housing'),
    # Investment
    (r'\b(MUTUAL\s*FUND|SIP|STOCK|SHARE|ZERODHA|GROWW|DEMAT|TRADING|INVESTMENT|DIVIDEND|INTEREST)\b', 'Investment'),
    # Salary / Income
    (r'\b(SALARY|PAYROLL|WAGE|STIPEND|FREELANCE|CONSULTING\s*FEE|BONUS)\b', 'Salary'),
    # Own Account Transfer (must be BEFORE generic Transfer to take priority)
    (r'(?:OWN\s*ACCOUNT|SELF)\s*TR\s*ANSFER|TR\s*ANSFER\s*(?:FROM|TO)\s*OWN\s*ACCOUNT|FROM\s*OWN\s*ACCOUNT|TO\s*OWN\s*ACCOUNT|TRANSFER\s*FROM\s*OWN|TRANSFER\s*TO\s*OWN|SELF\s*TRANSFER|ACCOUNT\s*TRANSFER\s*(?:FROM|TO)\s*(?:SAVING|CURRENT|OWN)', 'Own Account Transfer'),
    # Credit Card Bill Payment
    (r'CARD\s*BILL\s*PAYMENT|BILL\s*CA\s*RD.*PAID|CC\s*BILL\s*PAY|CREDIT\s*CARD\s*PAYMENT|CARD\s*PAYMENT.*BANKDIRECT|CC\s*PAYMENT|BILL\s*PAYMENT.*CARD|CARD.*BILL.*PAID|PAID\s*USING\s*BANKDIRECT', 'CC Bill Payment'),
    # Transfer
    (r'\b(TRANSFER|TRF|FUND\s*TRANSFER)\b', 'Transfer'),
    # ATM
    (r'\b(ATM|CASH\s*WITHDRAWAL)\b', 'Cash'),
    # Government / Tax
    (r'\b(TAX|GST|INCOME\s*TAX|TDS|GOVERNMENT|GOVT|CHALLAN)\b', 'Tax & Government'),
    # Entertainment
    (r'\b(MOVIE|CINEMA|THEATRE|CONCERT|PARK|MUSEUM|ENTERTAINMENT|GAMING|STEAM|PLAYSTATION|XBOX)\b', 'Entertainment'),
]

# ---------- Merchant name cleaning ----------

_NOISE_WORDS = re.compile(
    r'\b(POS|UPI|NEFT|IMPS|RTGS|ATM|NACH|ECS|ACH|WIRE|TRANSFER|TRF|TXN|REF|'
    r'CARD|CC|DEBIT|CREDIT|PAYMENT|PURCHASE|TRANSACTION|NO|NUMBER|INR|USD|QAR|'
    r'EUR|GBP|AED|SAR|DR|CR|INT\'?L|ONLINE|MOBILE|REVERSAL|REFUND|FEE|CHARGE|'
    r'S\.I|AUTO\-?PAY|SETTLEMENT|CLEARING|CASH|WITHDRAWAL|DEPOSIT)\b',
    re.IGNORECASE
)

_REF_NUMBER = re.compile(r'(?:REF\s*(?:NO|#)?\s*:?\s*)?[\dA-Z]{8,}')
_DATE_IN_DESC = re.compile(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}')
_MULTI_SPACE = re.compile(r'\s{2,}')


def enrich_transaction(description: str, raw_data: dict = None) -> Dict[str, Any]:
    """
    Extract rich metadata from a transaction description string.

    Returns dict with keys:
        merchant_name, merchant_category, transaction_method,
        location, card_last_four
    """
    if not description:
        return _empty_result()

    desc_upper = description.upper().strip()

    result: Dict[str, Any] = {
        "merchant_name": None,
        "merchant_category": None,
        "transaction_method": None,
        "location": None,
        "card_last_four": None,
    }

    # --- Transaction method ---
    for pattern, method in _METHOD_PATTERNS:
        if re.search(pattern, desc_upper):
            result["transaction_method"] = method
            break

    # --- Card last 4 ---
    for pattern in _CARD_PATTERNS:
        m = re.search(pattern, desc_upper)
        if m:
            result["card_last_four"] = m.group(1)
            break

    # --- Location ---
    for pattern in _LOCATION_PATTERNS:
        m = re.search(pattern, desc_upper)
        if m:
            loc = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else None
            if loc and len(loc) >= 2:
                result["location"] = loc.title()
                break

    # --- Category hint ---
    for pattern, category in _CATEGORY_HINTS:
        if re.search(pattern, desc_upper):
            result["merchant_category"] = category
            break

    # --- Merchant name (cleaned) ---
    result["merchant_name"] = _extract_merchant_name(description)

    return result


def _extract_merchant_name(description: str) -> Optional[str]:
    """Clean description to extract a usable merchant name."""
    name = description.strip()

    # Remove reference numbers
    name = _REF_NUMBER.sub('', name)
    # Remove embedded dates
    name = _DATE_IN_DESC.sub('', name)
    # Remove noise words
    name = _NOISE_WORDS.sub('', name)
    # Remove amounts like 123.45
    name = re.sub(r'[\d,]+\.\d{2}', '', name)
    # Remove special characters except &, ', -
    name = re.sub(r'[^\w\s&\'\-]', ' ', name)
    # Collapse whitespace
    name = _MULTI_SPACE.sub(' ', name).strip()
    # Remove leading/trailing hyphens
    name = name.strip('- ')

    if len(name) < 2:
        return None

    # Title case
    return name.title()


def _empty_result() -> Dict[str, Any]:
    return {
        "merchant_name": None,
        "merchant_category": None,
        "transaction_method": None,
        "location": None,
        "card_last_four": None,
    }
