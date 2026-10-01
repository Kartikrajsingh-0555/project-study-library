import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db = Path(self.directory.name) / "demo.sqlite3"

    def run_cli(self, *args, expected=0):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "app.py"),
                                 "--db", str(self.db), *map(str, args)],
                                cwd=self.directory.name, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr)
        if expected:
            self.assertNotIn("Traceback", result.stderr)
            return result.stderr
        return json.loads(result.stdout)

    def test_borrow_return_across_processes(self):
        resource = self.run_cli("add", "SQL notes", "DBMS")["resource_id"]
        member = self.run_cli("member", "Demo Student")["member_id"]
        loan = self.run_cli("borrow", resource, member)["loan_id"]
        self.assertEqual(self.run_cli("catalog")[0]["available"], 0)
        self.assertIsNone(self.run_cli("loans")[0]["returned_on"])
        self.run_cli("return", loan)
        self.assertEqual(self.run_cli("catalog")[0]["available"], 1)
        self.assertIsNotNone(self.run_cli("loans")[0]["returned_on"])
        self.run_cli("return", loan, expected=2)

    def test_seed_is_repeatable_from_another_directory(self):
        self.assertEqual(self.run_cli("seed"), {"added": 12, "total": 12})
        self.assertEqual(self.run_cli("seed"), {"added": 0, "total": 12})

    def test_invalid_commands_have_readable_errors(self):
        self.run_cli("add", "Invalid", "DSA", "--copies", 0, expected=2)
        self.run_cli("member", " ", expected=2)
        self.run_cli("borrow", 999, 999, expected=2)
        self.run_cli("borrow", 999, 999, "--days", 0, expected=2)
        self.assertEqual(self.run_cli("catalog"), [])

    def test_duplicate_member_and_unavailable_copy(self):
        resource = self.run_cli("add", "Notes", "DSA")["resource_id"]
        member = self.run_cli("member", "Student A")["member_id"]
        self.run_cli("member", "Student A", expected=2)
        other = self.run_cli("member", "Student B")["member_id"]
        self.run_cli("borrow", resource, member)
        self.assertIn("no copy available", self.run_cli("borrow", resource, other, expected=2))
        self.assertEqual(len(self.run_cli("loans")), 1)


if __name__ == "__main__":
    unittest.main()
