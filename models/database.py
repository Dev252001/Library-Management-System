import sqlite3
import os

# putting the db file in the project root, one level above this models/ folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "library.db")


def get_db():
    # opens a fresh connection each time — sqlite connections aren't thread-safe
    # so I'm not storing one globally
    conn = get_db._connect()
    # row_factory lets me do row["title"] instead of row[0] — much easier to read
    conn.row_factory = sqlite3.Row
    # sqlite ignores foreign keys by default, this turns that check on
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# small trick so I can mock the connect call in tests if needed
get_db._connect = lambda: sqlite3.connect(DB_PATH)


# the full schema — three tables, all created only if they don't exist yet
# so restarting the server never wipes data
SCHEMA = """
CREATE TABLE IF NOT EXISTS book (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT    NOT NULL,
    author           TEXT    NOT NULL,
    isbn             TEXT    UNIQUE,
    category         TEXT,
    total_copies     INTEGER NOT NULL DEFAULT 1 CHECK(total_copies >= 0),
    available_copies INTEGER NOT NULL DEFAULT 1
                     CHECK(available_copies >= 0
                           AND available_copies <= total_copies)
);

CREATE TABLE IF NOT EXISTS student (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    contact      TEXT,
    joining_date TEXT    NOT NULL DEFAULT (date('now')),
    fee_tier     TEXT    NOT NULL DEFAULT 'subsidized'
                 CHECK(fee_tier IN ('subsidized', 'standard'))
);

-- I named this borrow_transaction because 'transaction' is a reserved
-- keyword in SQLite and causes a syntax error if used as a table name
CREATE TABLE IF NOT EXISTS borrow_transaction (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id      INTEGER NOT NULL REFERENCES book(id),
    student_id   INTEGER NOT NULL REFERENCES student(id),
    issue_date   TEXT    NOT NULL DEFAULT (date('now')),
    due_date     TEXT    NOT NULL,
    return_date  TEXT,
    status       TEXT    NOT NULL DEFAULT 'issued'
                 CHECK(status IN ('issued', 'returned', 'overdue')),
    fine_amount  REAL    NOT NULL DEFAULT 0.0
);
"""


def init_db():
    # called once at startup from app.py — just creates the tables if missing
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        print(f"DB ready: {DB_PATH}")
    finally:
        conn.close()
