import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.financial.models import NormalizedFinancialValue

_AMOUNT = re.compile(
    r"^\s*(?P<open>\()?(?P<sign>[+\-−]?)\s*"
    r"(?P<currency>(?-i:[A-Z]{3})|[$€£₹¥])?\s*"
    r"(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*"
    r"(?P<scale>thousands?|millions?|billions?|lakhs?|lacs?|crores?|"
    r"thousand|million|billion|lakh|lac|crore|cr|mn|bn|[kmb])?\s*"
    r"(?P<percent>%|percent|percentage)?\s*(?P<currency_suffix>(?-i:[A-Z]{3}))?\s*(?(open)\))\s*$",
    re.IGNORECASE,
)
_SCALE = {
    "k": Decimal("1000"), "thousand": Decimal("1000"), "thousands": Decimal("1000"),
    "m": Decimal("1000000"), "mn": Decimal("1000000"), "million": Decimal("1000000"), "millions": Decimal("1000000"),
    "b": Decimal("1000000000"), "bn": Decimal("1000000000"), "billion": Decimal("1000000000"), "billions": Decimal("1000000000"),
    "lakh": Decimal("100000"), "lakhs": Decimal("100000"), "lac": Decimal("100000"), "lacs": Decimal("100000"),
    "crore": Decimal("10000000"), "crores": Decimal("10000000"), "cr": Decimal("10000000"),
}
_CODE_SYMBOLS = {"€": "EUR", "£": "GBP", "₹": "INR"}
_KNOWN_CURRENCY_CODES = frozenset(
    "USD EUR GBP INR CAD AUD SGD AED JPY CNY CHF NZD HKD KRW BRL MXN ZAR SEK NOK "
    "DKK PLN TRY IDR MYR THB PHP TWD VND BDT PKR SAR QAR EGP NGN KES ARS CLP COP "
    "PEN UYU ILS RUB UAH CZK HUF RON BGN ISK MAD TND JOD KWD BHD OMR LKR NPR GHS "
    "UGX TZS ETB XOF XAF XCD BSD BBD BMD KYD JMD TTD DOP CRC GTQ HNL NIO PAB PYG "
    "BOB GEL AMD AZN BYN BAM MKD RSD MDL ALL IQD IRR AFN KZT UZS"
    .split()
)


def normalize_financial_value(value: str) -> Optional[NormalizedFinancialValue]:
    """Parse one explicit amount without guessing an ambiguous currency."""
    match = _AMOUNT.fullmatch(value or "")
    if not match:
        return None
    try:
        amount = Decimal(match.group("number").replace(",", ""))
    except InvalidOperation:
        return None
    if match.group("open") or match.group("sign") in {"-", "−"}:
        amount = -amount
    scale = (match.group("scale") or "").lower()
    amount *= _SCALE.get(scale, Decimal(1))
    currency_token = match.group("currency") or match.group("currency_suffix") or ""
    if currency_token.isalpha() and currency_token.upper() not in _KNOWN_CURRENCY_CODES:
        return None
    currency_code = (
        currency_token.upper()
        if len(currency_token) == 3 and currency_token.isalpha()
        else _CODE_SYMBOLS.get(currency_token)
    )
    return NormalizedFinancialValue(
        normalized_value=amount,
        original_numeric_value=value.strip(),
        currency_code=currency_code,
        currency_symbol=currency_token if currency_token and not currency_token.isalpha() else None,
        original_unit_scale=scale or None,
        normalized_unit="percent" if match.group("percent") else "currency",
    )
