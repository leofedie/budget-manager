"""Budget rules, independent of terminal prompts and file I/O."""
from decimal import Decimal
from .validation import make_transaction, validate_month, CATEGORIES


def add_transaction(transactions, date, kind, category, amount, currency="EUR"):
    # Generate the next ID from the current records, not the list length.
    next_id = max((int(t.id[1:]) for t in transactions), default=0) + 1
    transaction = make_transaction(f"T{next_id:03d}", date, kind, category,
                                   amount, currency)
    transactions.append(transaction)
    return transaction


def filter_transactions(transactions, month=None, category=None):
    if month is not None:
        month = validate_month(month)
    if category is not None:
        category = category.strip().lower()
        if not any(category in categories for categories in CATEGORIES.values()):
            raise ValueError(f"unknown category '{category}'.")
    return [t for t in transactions
            if (month is None or t.date.startswith(month + "-"))
            and (category is None or t.category == category)]


def summarize(transactions):
    """Return income, expenses, balance and expense categories per currency."""
    report = {}
    for t in transactions:
        totals = report.setdefault(t.currency, {
            "income": Decimal("0.00"), "expenses": Decimal("0.00"),
            "balance": Decimal("0.00"), "categories": {},
        })
        amount = Decimal(str(t.amount))
        if t.kind == "income":
            totals["income"] += amount
        else:
            totals["expenses"] += amount
            categories = totals["categories"]
            categories[t.category] = categories.get(t.category, Decimal("0.00")) + amount
        totals["balance"] = totals["income"] - totals["expenses"]
    return report


def undo_last(transactions):
    """Remove the last added transaction, regardless of its transaction date."""
    if not transactions:
        raise ValueError("no transactions to undo.")
    return transactions.pop()
