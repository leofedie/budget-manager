"""Shared validation for new transactions and imported CSV rows."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from .models import Transaction

CATEGORIES = {
    "expense": ("food", "housing", "transport", "utilities", "health",
                "education", "entertainment", "other"),
    "income": ("salary", "freelance", "gift", "other"),
}
CURRENCIES = ("EUR", "USD", "GBP")


def validate_amount(raw):
    """Accept positive numeric amounts in cents, within Release 1's limit."""
    try:
        number = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        raise ValueError("amount must be a number, e.g. 18.50.") from None
    if not number.is_finite() or number <= 0:
        raise ValueError("amount must be > 0 and finite.")
    if number > 1_000_000_000:
        raise ValueError("amount must not exceed 1000000000.")
    if number != number.quantize(Decimal("0.01")):
        raise ValueError("amount must have at most two decimal places.")
    return float(number)


def validate_date(raw):
    value = str(raw).strip()
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("date must be a valid YYYY-MM-DD date.") from None
    if parsed.isoformat() != value:
        raise ValueError("date must be in YYYY-MM-DD format.")
    return value


def validate_month(raw):
    value = str(raw).strip()
    validate_date(value + "-01")
    return value


def make_transaction(id, date, kind, category, amount, currency):
    """Clean unambiguous text and reject invalid or ambiguous data."""
    id = str(id).strip()
    if not re.fullmatch(r"T[0-9]{3,}", id) or int(id[1:]) == 0:
        raise ValueError("id must be a positive transaction ID, e.g. T001.")
    date = validate_date(date)
    kind = str(kind).strip().lower()
    if kind not in CATEGORIES:
        raise ValueError("kind must be expense or income.")
    category = str(category).strip().lower()
    if category not in CATEGORIES[kind]:
        allowed = ", ".join(CATEGORIES[kind])
        raise ValueError(f"unknown {kind} category '{category}'; choose {allowed}.")
    amount = validate_amount(amount)
    currency = str(currency).strip().upper()
    if currency not in CURRENCIES:
        raise ValueError("currency must be EUR, USD or GBP.")
    return Transaction(id, date, kind, category, amount, currency)
