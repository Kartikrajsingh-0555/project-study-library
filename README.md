# Study Library

A local SQLite catalog for lending study resources. Track copies, members and borrowing history from the command line.

## Run

Requires Python 3.11+ with SQLite support. No additional packages are needed. From this directory:

```sh
python app.py seed
python app.py catalog
python app.py member "Demo Student"
python app.py borrow 1 1
python app.py loans
python app.py return 1
```

The example IDs assume a new database. Creation commands return IDs; use those values on subsequent runs. A successful borrow reduces availability, and returning it restores availability while retaining the loan record.

The default database is `artifacts/library.sqlite3`, which is excluded from Git. To use another file, place `--db` before the command:

```sh
python app.py --db demo.sqlite3 seed
python app.py --db demo.sqlite3 add "SQL practice notes" DBMS --description "joins and transactions" --copies 2
```

## Commands

| Command | Behaviour |
| --- | --- |
| `init` | Create database tables if missing |
| `seed` | Import missing fictional sample resources |
| `catalog` | Show resources, total copies and availability |
| `add TITLE SUBJECT --copies N` | Add a resource |
| `member NAME` / `members` | Register or list members |
| `borrow RESOURCE_ID MEMBER_ID --days 14` | Record a loan, if a copy is available |
| `return LOAN_ID` | Return an active loan |
| `loans` | List active and returned loan history |

Commands print JSON. Validation and database errors print to stderr and return exit code 2. Loan duration must be between 1 and 90 days. The due date uses the machine's local calendar date.

## Data and transactions

Resources and members are separate records referenced by loans. Availability is derived from total copies minus active loans. See [the schema](docs/schema.md).

Borrowing begins an `IMMEDIATE` SQLite transaction before checking stock. This prevents two app connections from allocating the same last copy. A partial unique index prevents a member from holding two active loans for one resource. Foreign keys are enabled on every connection; values use SQL parameters.

Seeding validates the entire input before importing records in one transaction. Repeated seeding skips existing title/subject pairs without changing their stock or loan history.

`data/resources.json` contains twelve fictional resource descriptions, integrated from the earlier local prototype. They are demonstration records, not a bibliography of published books. The lending core is adapted from that prototype; sample imports are now transactional and covered by CLI tests.

## Tests

```sh
python -B -m unittest discover -s tests -v
```

Tests cover persistence across separate CLI processes, stock exhaustion, returns, invalid dates, SQL parameter binding, sample imports and two concurrent requests for the last copy. Test databases use temporary directories.

## Current scope

- [x] SQLite catalog, members and loan history
- [x] Transactional borrowing and returns
- [x] Fictional sample data and CLI tests
- [ ] TF-IDF search and related-resource recommendations
- [ ] Overdue and member-specific loan reports

This is a local administration tool without login or permissions. Member names are unique, which is too restrictive for a real student directory. Copies are counts rather than individual barcodes. Direct database edits can bypass the application's stock checks; use the CLI for lending.
