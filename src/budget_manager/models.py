"""A consistent record structure for all transactions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Transaction:
    id: str
    date: str
    kind: str
    category: str
    amount: float
    currency: str


FIELDS = ("id", "date", "kind", "category", "amount", "currency")
