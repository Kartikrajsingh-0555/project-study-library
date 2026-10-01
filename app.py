"""Manage a local resource catalog and borrowing records."""
import argparse
import json
from pathlib import Path
import sqlite3
from library import Library

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "artifacts/library.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "catalog", "members", "loans"):
        sub.add_parser(name)
    sub.add_parser("seed", help="add missing fictional sample resources")
    member = sub.add_parser("member")
    member.add_argument("name")
    add = sub.add_parser("add")
    add.add_argument("title")
    add.add_argument("subject")
    add.add_argument("--description", default="")
    add.add_argument("--copies", type=int, default=1)
    borrow = sub.add_parser("borrow")
    borrow.add_argument("resource_id", type=int)
    borrow.add_argument("member_id", type=int)
    borrow.add_argument("--days", type=int, default=14)
    returns = sub.add_parser("return")
    returns.add_argument("loan_id", type=int)
    args = parser.parse_args()
    library = Library(args.db)
    try:
        library.initialize()
        if args.command == "init":
            result = {"database": str(args.db)}
        elif args.command == "seed":
            rows = json.loads((ROOT / "data/resources.json").read_text(encoding="utf-8"))
            result = {"added": library.seed(rows), "total": len(library.catalog())}
        elif args.command == "catalog":
            result = library.catalog()
        elif args.command == "members":
            result = library.members()
        elif args.command == "loans":
            result = library.loans()
        elif args.command == "member":
            result = {"member_id": library.add_member(args.name)}
        elif args.command == "add":
            result = {"resource_id": library.add_resource(args.title, args.subject, args.description, args.copies)}
        elif args.command == "borrow":
            result = {"loan_id": library.borrow(args.resource_id, args.member_id, args.days)}
        else:
            library.return_loan(args.loan_id)
            result = {"returned": args.loan_id}
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
