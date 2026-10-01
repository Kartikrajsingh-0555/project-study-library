from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from library import Library


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.library = Library(Path(self.directory.name) / "test.sqlite3")
        self.library.initialize()
        self.resource = self.library.add_resource("Graph practice", "DSA", "graphs paths heaps")
        self.member = self.library.add_member("Demo Student")

    def test_persistence(self):
        reopened = Library(self.library.path)
        self.assertEqual(reopened.catalog()[0]["title"], "Graph practice")

    def test_seed_validation_leaves_no_partial_import(self):
        with self.assertRaises(ValueError):
            self.library.seed([{"title": "Valid", "subject": "DSA"},
                               {"title": "Invalid", "subject": "DSA", "copies": 0}])
        self.assertEqual(len(self.library.catalog()), 1)

    def test_seed_preserves_existing_stock(self):
        rows = [{"title": "Graph practice", "subject": "DSA", "copies": 99},
                {"title": "New notes", "subject": "DBMS", "copies": 2}]
        self.assertEqual(self.library.seed(rows), 1)
        self.assertEqual(self.library.seed(rows), 0)
        self.assertEqual(self.library.catalog()[0]["copies"], 1)

    def test_invalid_inputs(self):
        for copies in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                self.library.add_resource("Notes", "DSA", copies=copies)
        with self.assertRaises(ValueError):
            self.library.add_member(None)
        for days in (0, 91, True):
            with self.assertRaises(ValueError):
                self.library.borrow(self.resource, self.member, days=days)

    def test_due_date_and_return_date_constraint(self):
        from datetime import date
        loan = self.library.borrow(self.resource, self.member, days=14, today=date(2026, 9, 30))
        self.assertEqual(self.library.loans()[0]["due_on"], "2026-10-14")
        with self.assertRaises(sqlite3.IntegrityError):
            self.library.return_loan(loan, today=date(2026, 9, 29))
        self.assertIsNone(self.library.loans()[0]["returned_on"])

    def test_foreign_keys_enabled_on_connections(self):
        from contextlib import closing
        with closing(self.library.connect()) as db, db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("""INSERT INTO loans(resource_id,member_id,borrowed_on,due_on)
                           VALUES(999,999,'2026-10-01','2026-10-15')""")

    def test_borrow_and_return(self):
        loan = self.library.borrow(self.resource, self.member)
        self.assertEqual(self.library.catalog()[0]["available"], 0)
        self.library.return_loan(loan)
        self.assertEqual(self.library.catalog()[0]["available"], 1)

    def test_duplicate_return(self):
        loan = self.library.borrow(self.resource, self.member)
        self.library.return_loan(loan)
        with self.assertRaises(ValueError):
            self.library.return_loan(loan)

    def test_stock_exhaustion_rolls_back(self):
        self.library.borrow(self.resource, self.member)
        other = self.library.add_member("Other Student")
        with self.assertRaises(ValueError):
            self.library.borrow(self.resource, other)
        self.assertEqual(len(self.library.loans()), 1)

    def test_missing_member_does_not_consume_stock(self):
        with self.assertRaises(ValueError):
            self.library.borrow(self.resource, 999)
        self.assertEqual(self.library.catalog()[0]["available"], 1)


    def test_duplicate_loan_constraint(self):
        book = self.library.add_resource("SQL", "DBMS", copies=2)
        self.library.borrow(book, self.member)
        with self.assertRaises(sqlite3.IntegrityError):
            self.library.borrow(book, self.member)
        self.assertEqual(len(self.library.loans()), 1)

    def test_sql_injection_is_stored_as_data(self):
        name = "x'); DROP TABLE resources; --"
        self.library.add_member(name)
        self.assertEqual(len(self.library.catalog()), 1)
        self.assertEqual(self.library.members()[1]["name"], name)

    def test_concurrent_last_copy(self):
        other = self.library.add_member("Other Student")
        def attempt(member):
            try:
                self.library.borrow(self.resource, member)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [self.member, other]))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.library.catalog()[0]["available"], 0)





if __name__ == "__main__":
    unittest.main()
