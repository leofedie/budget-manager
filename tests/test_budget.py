"""Normal cases, boundaries, malformed files and end-to-end behavior."""
import subprocess
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.budget_manager.services import add_transaction, filter_transactions, summarize
from src.budget_manager.storage import load_transactions, save_transactions, backup_transactions
from src.budget_manager.validation import make_transaction

ROOT = Path(__file__).resolve().parents[1]


class BudgetTests(unittest.TestCase):
    def test_normal_balance(self):
        records = []
        add_transaction(records, "2026-09-01", "income", "salary", 100)
        add_transaction(records, "2026-09-04", "expense", "food", 18.5)
        self.assertEqual(records[1].id, "T002")
        totals = summarize(records)["EUR"]
        self.assertEqual(totals["income"], Decimal("100.00"))
        self.assertEqual(totals["expenses"], Decimal("18.50"))
        self.assertEqual(totals["balance"], Decimal("81.50"))
        self.assertEqual(totals["categories"]["food"], Decimal("18.50"))

    def test_invalid_amounts(self):
        records = []
        for amount in (-1, 0, "abc", "nan", "inf", "0.001", "1000000001"):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(ValueError, "amount"):
                    add_transaction(records, "2026-09-04", "expense", "food", amount)
        self.assertEqual(records, [])
        add_transaction(records, "2026-09-04", "expense", "food", "0.01")
        self.assertEqual(records[0].amount, 0.01)

    def test_unknown_category_and_kind(self):
        for kind, category in (("expense", "unknown"), ("income", "food")):
            with self.subTest(kind=kind, category=category):
                with self.assertRaisesRegex(ValueError, "unknown .* category"):
                    make_transaction("T001", "2026-09-04", kind, category, 20, "EUR")
        with self.assertRaisesRegex(ValueError, "kind"):
            make_transaction("T001", "2026-09-04", "transfer", "food", 20, "EUR")

    def test_invalid_date_and_currency(self):
        for value in ("2026-02-30", "20260904", "04/09/2026"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "date"):
                    make_transaction("T001", value, "expense", "food", 20, "EUR")
        with self.assertRaisesRegex(ValueError, "currency"):
            make_transaction("T001", "2026-09-04", "expense", "food", 20, "XYZ")

    def test_cleaning(self):
        t = make_transaction(" T001 ", "2026-09-04", " Expense ", " FOOD ", " 18.50 ", "eur")
        self.assertEqual((t.id, t.kind, t.category, t.amount, t.currency),
                         ("T001", "expense", "food", 18.5, "EUR"))

    def test_filter_and_separate_currencies(self):
        records = load_transactions(ROOT / "data/sample_transactions.csv")
        september = filter_transactions(records, month="2026-09")
        totals = summarize(september)
        self.assertEqual(totals["EUR"]["balance"], Decimal("856.50"))
        self.assertEqual(totals["USD"]["balance"], Decimal("90.00"))
        self.assertEqual(len(filter_transactions(september, category="food")), 2)
        with self.assertRaisesRegex(ValueError, "date"):
            filter_transactions(records, month="2026-13")
        self.assertEqual(summarize([]), {})

    def test_persistence_round_trip_and_backup(self):
        records = load_transactions(ROOT / "data/sample_transactions.csv")
        with TemporaryDirectory() as folder:
            path = Path(folder) / "transactions.csv"
            backup = Path(folder) / "backup.csv"
            self.assertEqual(load_transactions(path), [])
            save_transactions(path, records)
            self.assertEqual(load_transactions(path), records)
            backup_transactions(backup, records)
            self.assertEqual(load_transactions(backup), records)
            self.assertEqual(path.read_bytes(), backup.read_bytes())
            with self.assertRaises(FileExistsError):
                backup_transactions(backup, [])
            self.assertEqual(load_transactions(backup), records)

    def test_invalid_import_reports_row(self):
        with self.assertRaisesRegex(ValueError, r"Row 3: amount must be > 0"):
            load_transactions(ROOT / "data/sample_invalid_transactions.csv")

    def test_duplicate_id_and_bad_header(self):
        header = "id,date,kind,category,amount,currency\n"
        row = "T001,2026-09-04,expense,food,18.50,EUR\n"
        with TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            path.write_text(header + row + row, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Row 3: duplicate id"):
                load_transactions(path)
            path.write_text("wrong,header\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Row 1: expected CSV header"):
                load_transactions(path)

    def test_failed_save_preserves_previous_file(self):
        records = load_transactions(ROOT / "data/sample_transactions.csv")
        with TemporaryDirectory() as folder:
            path = Path(folder) / "transactions.csv"
            save_transactions(path, records)
            before = path.read_bytes()
            with patch("src.budget_manager.storage.os.replace", side_effect=OSError("simulated failure")):
                with self.assertRaises(OSError):
                    save_transactions(path, [])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_cli_end_to_end_and_undo(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "live.csv"

            def run(*args):
                return subprocess.run([sys.executable, str(ROOT / "budget.py"),
                                       "--file", str(path), *args],
                                      capture_output=True, text=True)

            self.assertEqual(run("add", "100", "--kind", "income", "--category", "salary").returncode, 0)
            self.assertEqual(run("add", "18.50", "--category", "food").returncode, 0)
            self.assertIn("T002", run("list").stdout)
            self.assertIn("Balance:  81.50", run("summary").stdout)
            before = path.read_bytes()
            invalid = run("add", "-5", "--category", "food")
            self.assertEqual(invalid.returncode, 2)
            self.assertIn("amount must be > 0", invalid.stderr)
            self.assertEqual(invalid.stdout, "")
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(run("undo").returncode, 0)
            self.assertIn("Balance:  100.00", run("summary").stdout)
            self.assertEqual(len(load_transactions(path)), 1)
            self.assertEqual(run("undo").returncode, 0)
            self.assertEqual(run("undo").returncode, 2)
            self.assertEqual(load_transactions(path), [])


if __name__ == "__main__":
    unittest.main()
