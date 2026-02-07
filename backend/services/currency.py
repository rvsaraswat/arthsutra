"""
CurrencyService — Multi-currency conversion, formatting, and metadata.

Supports 50+ international currencies with:
- Real-time conversion via CurrencyConverter (ECB rates)
- Fallback static rates for currencies not in ECB (QAR, AED, SAR, etc.)
- Symbol/locale formatting
- Thread-safe caching
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from currency_converter import CurrencyConverter
import threading

# ---------- Currency metadata ----------

CURRENCY_INFO: Dict[str, Dict] = {
    "INR": {"symbol": "₹", "name": "Indian Rupee", "locale": "en-IN"},
    "USD": {"symbol": "$", "name": "US Dollar", "locale": "en-US"},
    "EUR": {"symbol": "€", "name": "Euro", "locale": "de-DE"},
    "GBP": {"symbol": "£", "name": "British Pound", "locale": "en-GB"},
    "QAR": {"symbol": "QR", "name": "Qatari Riyal", "locale": "ar-QA"},
    "AED": {"symbol": "د.إ", "name": "UAE Dirham", "locale": "ar-AE"},
    "SAR": {"symbol": "SR", "name": "Saudi Riyal", "locale": "ar-SA"},
    "BHD": {"symbol": "BD", "name": "Bahraini Dinar", "locale": "ar-BH"},
    "KWD": {"symbol": "KD", "name": "Kuwaiti Dinar", "locale": "ar-KW"},
    "OMR": {"symbol": "OMR", "name": "Omani Rial", "locale": "ar-OM"},
    "JPY": {"symbol": "¥", "name": "Japanese Yen", "locale": "ja-JP"},
    "CNY": {"symbol": "¥", "name": "Chinese Yuan", "locale": "zh-CN"},
    "CAD": {"symbol": "C$", "name": "Canadian Dollar", "locale": "en-CA"},
    "AUD": {"symbol": "A$", "name": "Australian Dollar", "locale": "en-AU"},
    "NZD": {"symbol": "NZ$", "name": "New Zealand Dollar", "locale": "en-NZ"},
    "CHF": {"symbol": "CHF", "name": "Swiss Franc", "locale": "de-CH"},
    "SGD": {"symbol": "S$", "name": "Singapore Dollar", "locale": "en-SG"},
    "HKD": {"symbol": "HK$", "name": "Hong Kong Dollar", "locale": "en-HK"},
    "SEK": {"symbol": "kr", "name": "Swedish Krona", "locale": "sv-SE"},
    "NOK": {"symbol": "kr", "name": "Norwegian Krone", "locale": "nb-NO"},
    "DKK": {"symbol": "kr", "name": "Danish Krone", "locale": "da-DK"},
    "ZAR": {"symbol": "R", "name": "South African Rand", "locale": "en-ZA"},
    "MYR": {"symbol": "RM", "name": "Malaysian Ringgit", "locale": "ms-MY"},
    "THB": {"symbol": "฿", "name": "Thai Baht", "locale": "th-TH"},
    "PHP": {"symbol": "₱", "name": "Philippine Peso", "locale": "en-PH"},
    "IDR": {"symbol": "Rp", "name": "Indonesian Rupiah", "locale": "id-ID"},
    "KRW": {"symbol": "₩", "name": "South Korean Won", "locale": "ko-KR"},
    "TRY": {"symbol": "₺", "name": "Turkish Lira", "locale": "tr-TR"},
    "BRL": {"symbol": "R$", "name": "Brazilian Real", "locale": "pt-BR"},
    "MXN": {"symbol": "Mex$", "name": "Mexican Peso", "locale": "es-MX"},
    "PLN": {"symbol": "zł", "name": "Polish Zloty", "locale": "pl-PL"},
    "CZK": {"symbol": "Kč", "name": "Czech Koruna", "locale": "cs-CZ"},
    "HUF": {"symbol": "Ft", "name": "Hungarian Forint", "locale": "hu-HU"},
    "RUB": {"symbol": "₽", "name": "Russian Ruble", "locale": "ru-RU"},
    "EGP": {"symbol": "E£", "name": "Egyptian Pound", "locale": "ar-EG"},
    "NGN": {"symbol": "₦", "name": "Nigerian Naira", "locale": "en-NG"},
    "KES": {"symbol": "KSh", "name": "Kenyan Shilling", "locale": "en-KE"},
    "PKR": {"symbol": "₨", "name": "Pakistani Rupee", "locale": "ur-PK"},
    "BDT": {"symbol": "৳", "name": "Bangladeshi Taka", "locale": "bn-BD"},
    "LKR": {"symbol": "Rs", "name": "Sri Lankan Rupee", "locale": "si-LK"},
    "NPR": {"symbol": "Rs", "name": "Nepalese Rupee", "locale": "ne-NP"},
    "TWD": {"symbol": "NT$", "name": "Taiwan Dollar", "locale": "zh-TW"},
    "VND": {"symbol": "₫", "name": "Vietnamese Dong", "locale": "vi-VN"},
    "CLP": {"symbol": "CL$", "name": "Chilean Peso", "locale": "es-CL"},
    "COP": {"symbol": "COL$", "name": "Colombian Peso", "locale": "es-CO"},
    "ARS": {"symbol": "AR$", "name": "Argentine Peso", "locale": "es-AR"},
    "PEN": {"symbol": "S/.", "name": "Peruvian Sol", "locale": "es-PE"},
    "ILS": {"symbol": "₪", "name": "Israeli Shekel", "locale": "he-IL"},
    "JOD": {"symbol": "JD", "name": "Jordanian Dinar", "locale": "ar-JO"},
}

# Static USD-based fallback rates for currencies not covered by ECB
# (Gulf currencies are USD-pegged, so these are stable)
_STATIC_USD_RATES: Dict[str, float] = {
    "QAR": 3.64,
    "AED": 3.6725,
    "SAR": 3.75,
    "BHD": 0.376,
    "KWD": 0.307,
    "OMR": 0.385,
    "EGP": 50.5,
    "NGN": 1550.0,
    "KES": 129.0,
    "PKR": 278.0,
    "BDT": 121.0,
    "LKR": 298.0,
    "NPR": 133.5,
    "VND": 25350.0,
    "ARS": 1050.0,
}


class CurrencyService:
    """Thread-safe currency conversion with caching."""

    def __init__(self):
        self._lock = threading.Lock()
        self._converter: Optional[CurrencyConverter] = None
        self._cache: Dict[str, Tuple[float, datetime]] = {}
        self._cache_ttl = timedelta(hours=6)
        self._init_converter()

    def _init_converter(self):
        try:
            self._converter = CurrencyConverter()
        except Exception:
            self._converter = None
            print("[CurrencyService] WARNING: CurrencyConverter init failed, using static rates only")

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def get_supported_currencies(self):
        """Return list of supported currencies with metadata."""
        return [
            {"code": code, **info}
            for code, info in sorted(CURRENCY_INFO.items(), key=lambda x: x[0])
        ]

    def get_symbol(self, currency_code: str) -> str:
        info = CURRENCY_INFO.get(currency_code.upper())
        return info["symbol"] if info else currency_code.upper()

    def get_rate(self, from_currency: str, to_currency: str, date: Optional[datetime] = None) -> float:
        """Get exchange rate from_currency → to_currency."""
        frm = from_currency.upper()
        to = to_currency.upper()

        if frm == to:
            return 1.0

        cache_key = f"{frm}_{to}_{(date or datetime.utcnow()).strftime('%Y-%m-%d')}"
        with self._lock:
            if cache_key in self._cache:
                rate, cached_at = self._cache[cache_key]
                if datetime.utcnow() - cached_at < self._cache_ttl:
                    return rate

        # Strategy 1: CurrencyConverter (ECB data)
        rate = self._try_ecb(frm, to, date)
        if rate is not None:
            self._set_cache(cache_key, rate)
            return rate

        # Strategy 2: Static USD pivot
        rate = self._try_static_pivot(frm, to)
        if rate is not None:
            self._set_cache(cache_key, rate)
            return rate

        # Fallback: return 1.0 and log warning
        print(f"[CurrencyService] WARNING: No rate for {frm} → {to}, returning 1.0")
        return 1.0

    def convert(self, amount: float, from_currency: str, to_currency: str,
                date: Optional[datetime] = None) -> float:
        """Convert amount between currencies."""
        rate = self.get_rate(from_currency, to_currency, date)
        return round(amount * rate, 2)

    def format_amount(self, amount: float, currency_code: str) -> str:
        """Format an amount with the correct symbol."""
        symbol = self.get_symbol(currency_code)
        abs_amount = abs(amount)
        sign = "-" if amount < 0 else ""

        # Currencies with no decimal (JPY, KRW, VND, etc.)
        no_decimal = {"JPY", "KRW", "VND", "CLP", "IDR", "HUF"}
        if currency_code.upper() in no_decimal:
            formatted = f"{abs_amount:,.0f}"
        else:
            formatted = f"{abs_amount:,.2f}"

        return f"{sign}{symbol}{formatted}"

    # --------------------------------------------------
    # Private helpers
    # --------------------------------------------------

    def _try_ecb(self, frm: str, to: str, date: Optional[datetime]) -> Optional[float]:
        if not self._converter:
            return None
        try:
            if date:
                rate = self._converter.convert(1.0, frm, to, date=date)
            else:
                rate = self._converter.convert(1.0, frm, to)
            return float(rate)
        except Exception:
            return None

    def _try_static_pivot(self, frm: str, to: str) -> Optional[float]:
        """Convert via USD using static rates."""
        # Get both currencies in terms of USD
        usd_to_frm = self._usd_rate_for(frm)
        usd_to_to = self._usd_rate_for(to)

        if usd_to_frm is None or usd_to_to is None:
            return None

        # frm → USD → to
        # 1 frm = (1 / usd_to_frm) USD = (usd_to_to / usd_to_frm) to
        return usd_to_to / usd_to_frm

    def _usd_rate_for(self, currency: str) -> Optional[float]:
        """How many units of `currency` per 1 USD."""
        if currency == "USD":
            return 1.0

        # Check static table
        if currency in _STATIC_USD_RATES:
            return _STATIC_USD_RATES[currency]

        # Try ECB: 1 USD → ? currency
        if self._converter:
            try:
                return float(self._converter.convert(1.0, "USD", currency))
            except Exception:
                pass

        return None

    def _set_cache(self, key: str, rate: float):
        with self._lock:
            self._cache[key] = (rate, datetime.utcnow())


# Module-level singleton
currency_service = CurrencyService()
