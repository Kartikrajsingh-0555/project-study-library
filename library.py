"""SQLite catalog and transactional resource lending."""
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
    subject TEXT NOT NULL CHECK(length(trim(subject)) > 0),
    description TEXT NOT NULL,
    copies INTEGER NOT NULL CHECK(copies > 0),
    UNIQUE(title, subject)
);
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) > 0)
);
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    member_id INTEGER NOT NULL REFERENCES members(id),
    borrowed_on TEXT NOT NULL,
    due_on TEXT NOT NULL,
    returned_on TEXT,
    CHECK(due_on >= borrowed_on),
    CHECK(returned_on IS NULL OR returned_on >= borrowed_on)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_loan
ON loans(resource_id, member_id) WHERE returned_on IS NULL;
CREATE INDEX IF NOT EXISTS active_resource_loans ON loans(resource_id) WHERE returned_on IS NULL;
"""


class Library:
    def __init__(self, path):
        self.path = Path(path)

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.executescript(SCHEMA)

    def add_resource(self, title, subject, description="", copies=1):
        title, subject, description, copies = self.validate_resource(title, subject, description, copies)
        with closing(self.connect()) as db, db:
            cursor = db.execute("INSERT INTO resources(title,subject,description,copies) VALUES(?,?,?,?)",
                                (title, subject, description, copies))
            return cursor.lastrowid

    @staticmethod
    def validate_resource(title, subject, description="", copies=1):
        if not isinstance(title, str) or not isinstance(subject, str) or not isinstance(description, str):
            raise ValueError("resource fields must be strings")
        if not title.strip() or not subject.strip() or type(copies) is not int or copies < 1:
            raise ValueError("title, subject and positive integer copies required")
        return title.strip(), subject.strip(), description.strip(), copies

    def seed(self, rows):
        """Import missing records atomically without overwriting existing stock."""
        if not isinstance(rows, list):
            raise ValueError("sample resources must be a list")
        values = []
        for row in rows:
            if not isinstance(row, dict) or not {"title", "subject"} <= row.keys():
                raise ValueError("sample resources require title and subject")
            values.append(self.validate_resource(row["title"], row["subject"],
                                                row.get("description", ""), row.get("copies", 1)))
        with closing(self.connect()) as db, db:
            before = db.total_changes
            db.executemany("""INSERT INTO resources(title,subject,description,copies) VALUES(?,?,?,?)
                           ON CONFLICT(title,subject) DO NOTHING""", values)
            return db.total_changes - before

    def add_member(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("member name required")
        with closing(self.connect()) as db, db:
            return db.execute("INSERT INTO members(name) VALUES(?)", (name.strip(),)).lastrowid

    def catalog(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("""
                SELECT r.*, r.copies - COUNT(l.id) AS available FROM resources r
                LEFT JOIN loans l ON r.id=l.resource_id AND l.returned_on IS NULL
                GROUP BY r.id ORDER BY r.id
            """)]

    def members(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("SELECT * FROM members ORDER BY id")]

    def borrow(self, resource_id, member_id, days=14, today=None):
        if type(days) is not int or not 1 <= days <= 90:
            raise ValueError("loan duration must be 1 to 90 days")
        today = today or date.today()
        with closing(self.connect()) as db, db:
            # Lock before reading availability: two writers cannot allocate the last copy.
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT copies FROM resources WHERE id=?", (resource_id,)).fetchone()
            if row is None:
                raise ValueError("resource not found")
            if db.execute("SELECT id FROM members WHERE id=?", (member_id,)).fetchone() is None:
                raise ValueError("member not found")
            active = db.execute("SELECT COUNT(*) FROM loans WHERE resource_id=? AND returned_on IS NULL", (resource_id,)).fetchone()[0]
            if active >= row["copies"]:
                raise ValueError("no copy available")
            return db.execute("INSERT INTO loans(resource_id,member_id,borrowed_on,due_on) VALUES(?,?,?,?)",
                              (resource_id, member_id, today.isoformat(), (today + timedelta(days=days)).isoformat())).lastrowid

    def return_loan(self, loan_id, today=None):
        today = today or date.today()
        with closing(self.connect()) as db, db:
            changed = db.execute("UPDATE loans SET returned_on=? WHERE id=? AND returned_on IS NULL",
                                 (today.isoformat(), loan_id)).rowcount
            if not changed:
                raise ValueError("active loan not found")

    def loans(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute("""
                SELECT l.*, r.title, m.name FROM loans l
                JOIN resources r ON r.id=l.resource_id
                JOIN members m ON m.id=l.member_id ORDER BY l.id
            """)]
