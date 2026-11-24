"""Command-line interface, adapted from the provided argparse example."""
import argparse
import sys
from datetime import date, datetime
from pathlib import Path
from .services import add_transaction, filter_transactions, summarize, undo_last
from .storage import load_transactions, save_transactions, backup_transactions

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE = ROOT / "data" / "transactions.csv"


def build_parser():
    parser = argparse.ArgumentParser(description="Personal Budget Manager")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE,
                        help="CSV data file (default: data/transactions.csv)")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="Add income or an expense")
    add.add_argument("amount", help="Positive amount, e.g. 18.50")
    add.add_argument("--category", required=True, help="Category, e.g. food")
    add.add_argument("--kind", default="expense", help="expense or income")
    add.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD")
    add.add_argument("--currency", default="EUR", help="EUR, USD or GBP")

    for name in ("list", "summary"):
        command = commands.add_parser(name, help=f"{name.capitalize()} transactions")
        command.add_argument("--month", help="Filter by YYYY-MM")
        command.add_argument("--category", help="Filter by category")

    backup = commands.add_parser("backup", help="Create a verified CSV backup")
    backup.add_argument("destination", nargs="?", type=Path,
                        help="New CSV file; defaults to a timestamped backup")
    commands.add_parser("undo", help="Remove the last added transaction")
    return parser


def show_transactions(transactions):
    if not transactions:
        print("No transactions.")
        return
    print(f"{'ID':<8} {'Date':<12} {'Kind':<9} {'Category':<15} {'Amount':>14}  Currency")
    for t in transactions:
        print(f"{t.id:<8} {t.date:<12} {t.kind:<9} {t.category:<15} {t.amount:>14.2f}  {t.currency}")


def show_summary(report):
    if not report:
        print("No transactions. Income: 0.00; Expenses: 0.00; Balance: 0.00.")
    for currency, totals in sorted(report.items()):
        print(f"Currency: {currency}")
        print(f"Income:   {totals['income']:.2f}")
        print(f"Expenses: {totals['expenses']:.2f}")
        print(f"Balance:  {totals['balance']:.2f}")
        if totals["categories"]:
            print("Expenses by category:")
            for category, amount in sorted(totals["categories"].items()):
                print(f"  {category}: {amount:.2f}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        transactions = load_transactions(args.file)
        if args.command == "add":
            t = add_transaction(transactions, args.date, args.kind, args.category,
                                args.amount, args.currency)
            save_transactions(args.file, transactions)
            print(f"Added {t.id}: {t.kind} {t.amount:.2f} {t.currency} ({t.category})")
        elif args.command in ("list", "summary"):
            selected = filter_transactions(transactions, args.month, args.category)
            if args.command == "list":
                show_transactions(selected)
            else:
                show_summary(summarize(selected))
        elif args.command == "backup":
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            destination = args.destination or ROOT / "backups" / f"transactions-{stamp}.csv"
            backup_transactions(destination, transactions)
            print(f"Backup verified: {destination}")
        elif args.command == "undo":
            removed = undo_last(transactions)
            save_transactions(args.file, transactions)
            print(f"Undid {removed.id}.")
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"File error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
