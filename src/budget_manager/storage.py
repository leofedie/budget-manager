"""CSV persistence; validate all imported rows before using any of them."""
import csv
import os
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile
from .models import FIELDS
from .validation import make_transaction


def load_transactions(path):
    path = Path(path)
    if not path.exists():
        return []
    transactions = []
    ids = set()
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        try:
            if reader.fieldnames != list(FIELDS):
                raise ValueError("Row 1: expected CSV header " + ",".join(FIELDS))
            for row in reader:
                try:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("wrong number of fields.")
                    transaction = make_transaction(**row)
                    if transaction.id in ids:
                        raise ValueError(f"duplicate id {transaction.id}.")
                except ValueError as error:
                    raise ValueError(f"Row {reader.line_num}: {error}") from None
                ids.add(transaction.id)
                transactions.append(transaction)
        except csv.Error as error:
            raise ValueError(f"Row {reader.line_num}: malformed CSV: {error}") from None
    return transactions


def _write_csv(file, transactions):
    writer = csv.DictWriter(file, fieldnames=FIELDS)
    writer.writeheader()
    for transaction in transactions:
        row = asdict(transaction)
        row["amount"] = f"{transaction.amount:.2f}"
        writer.writerow(row)


def save_transactions(path, transactions):
    """Write to a temporary file, then replace the old file in one operation."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                dir=path.parent, delete=False) as file:
            temporary_path = Path(file.name)
            _write_csv(file, transactions)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def backup_transactions(destination, transactions):
    """Create a new CSV backup; verify its contents; never overwrite a backup."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with destination.open("x", encoding="utf-8", newline="") as file:
            created = True
            _write_csv(file, transactions)
        if load_transactions(destination) != transactions:
            raise ValueError("backup verification failed.")
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
    return destination
